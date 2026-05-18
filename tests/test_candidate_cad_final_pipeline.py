from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["ACTIVE_MODEL_PROVIDER"] = "local"
os.environ["TEXT_AGENT_PROVIDER"] = "local"
os.environ["VISION_AGENT_PROVIDER"] = "local"
os.environ["A1_DB_PATH"] = str(ROOT / "data" / "test-maintenance.db")

from backend.app.database import reset_demo_db  # noqa: E402
from backend.app.main import app  # noqa: E402


def setup_module() -> None:
    reset_demo_db()


client = TestClient(app)


def _upload_demo_image(equipment: str = "pump") -> int:
    image_dir = ROOT / "data" / "image_eval" / "images"
    preferred = {
        "pump": "pump_mechanical_seal_parts_02.jpg",
        "bearing": "bearing_spalling_01.jpg",
    }.get(equipment, "pump_mechanical_seal_parts_02.jpg")
    image_path = image_dir / preferred
    if not image_path.exists():
        image_path = next(image_dir.glob("*.jpg"))
    with image_path.open("rb") as handle:
        response = client.post(
            "/api/upload-image",
            files={"file": (image_path.name, handle, "image/jpeg")},
        )
    assert response.status_code == 200
    return int(response.json()["visual_asset_id"])


def _create_candidate() -> dict:
    visual_asset_id = _upload_demo_image("pump")
    response = client.post(
        "/api/cad/candidates/from-visual",
        json={
            "visual_asset_id": visual_asset_id,
            "equipment": "pump",
            "model": "ISG80-160",
            "generator": "cadquery_openscad",
        },
    )
    assert response.status_code == 200
    return response.json()["candidate"]


def test_cad_runtime_probe_returns_declared_tools() -> None:
    response = client.get("/api/cad/runtime")
    assert response.status_code == 200
    report = response.json()
    assert report["schema_version"] == "cad-runtime-v1"
    assert {"cadquery", "freecad", "openscad", "blender", "trimesh", "pillow"} <= set(report["tools"])
    for tool in report["tools"].values():
        assert {"available", "command", "version", "role", "required_for_final"} <= set(tool)
    assert report["recommended_mode"] in {"real_render", "python_render", "partial_render", "code_only"}
    if all(report["tools"][name]["available"] for name in ["cadquery", "trimesh", "pillow", "freecad", "openscad", "blender"]):
        assert report["recommended_mode"] == "real_render"


def test_candidate_cad_generation_returns_real_artifact_manifest() -> None:
    candidate = _create_candidate()
    manifest = candidate["artifact_manifest"]
    assert manifest["schema_version"] == "candidate-cad-artifacts-v1"
    assert manifest["source_files"]["cadquery"]["exists"] is True
    assert manifest["source_files"]["openscad"]["exists"] is True
    assert manifest["source_files"]["cad_spec"]["exists"] is True
    assert manifest["cad_files"]["step"]["path"].endswith(".step")
    assert manifest["cad_files"]["step"]["exists"] is True
    assert manifest["cad_files"]["stl"]["path"].endswith(".stl")
    assert manifest["cad_files"]["stl"]["exists"] is True
    assert manifest["cad_files"]["glb"]["path"].endswith(".glb")
    assert manifest["cad_files"]["glb"]["exists"] is True
    assert manifest["renders"]["iso"]["path"].endswith(".png")
    assert manifest["renders"]["iso"]["exists"] is True
    assert candidate["runtime_report"]["recommended_mode"] in {"real_render", "python_render", "partial_render", "code_only"}
    if candidate["runtime_report"]["recommended_mode"] == "real_render":
        assert candidate["runtime_report"]["artifact_mode"] == "real_render"
        assert manifest["render_engine"] == "blender"
        assert manifest["cad_files"]["openscad_stl"]["exists"] is True
        assert manifest["quality_reports"]["freecad_validation"]["exists"] is True
        assert manifest["quality_reports"]["openscad_export"]["exists"] is True
        assert manifest["quality_reports"]["blender_render"]["exists"] is True
        stages = {item["stage"] for item in manifest["generation_log"]}
        assert {"freecad_step_validation", "openscad_export", "blender_multi_view_render"} <= stages
    assert candidate["comparison_report"]["status"] in {"pass", "needs_review", "reject"}


def test_candidate_cad_generation_does_not_hold_db_lock_during_render(monkeypatch, tmp_path: Path) -> None:
    from backend.app import candidate_cad
    from backend.app.database import init_db

    db_path = tmp_path / "candidate-lock.db"
    conn = sqlite3.connect(db_path, timeout=0.2)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    peer_write = {"ok": False}

    def fake_write_candidate_artifacts(*, artifact_dir: Path, observation: dict, spec: dict) -> dict:
        peer = sqlite3.connect(db_path, timeout=0.2)
        try:
            peer.execute(
                """
                INSERT INTO feedback
                (question, original_answer, corrected_answer, notes, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("lock probe", "before", "after", "candidate render phase", "2026-05-18T00:00:00"),
            )
            peer.commit()
            peer_write["ok"] = True
        finally:
            peer.close()
        return {
            "code_artifacts": {},
            "render_artifacts": {},
            "render_report": {},
            "comparison_report": {},
            "runtime_report": {},
            "artifact_manifest": {},
        }

    monkeypatch.setattr(candidate_cad, "_write_candidate_artifacts", fake_write_candidate_artifacts)
    candidate = candidate_cad.create_candidate_from_visual_asset(
        conn,
        {
            "id": 1,
            "filename": "pump_leak.jpg",
            "stored_path": "data/uploads/pump_leak.jpg",
            "caption": "泵机械密封泄漏",
            "model": "ISG80-160",
            "analysis": {
                "caption": "泵机械密封泄漏",
                "equipment_candidates": [{"id": "pump", "label": "离心泵", "confidence": 0.9}],
                "component_candidates": [{"label": "机械密封", "confidence": 0.86}],
                "defect_labels": [{"label": "泄漏", "confidence": 0.82}],
                "retrieval_keywords": ["离心泵", "机械密封", "泄漏"],
            },
        },
        equipment="pump",
        model="ISG80-160",
    )
    assert candidate["id"] > 0
    assert peer_write["ok"] is True
    conn.close()


def test_candidate_cad_spec_can_be_patched_and_regenerated() -> None:
    candidate = _create_candidate()
    response = client.patch(
        f"/api/cad/candidates/{candidate['id']}/spec",
        json={
            "parameters": {"body_length": 188, "port_diameter": 52},
            "component_keys": ["pump.casing", "pump.mechanical_seal", "pump.shaft"],
            "review_notes": "人工修正泵体长度和法兰口径，准备重新生成候选 CAD。",
        },
    )
    assert response.status_code == 200
    patched = response.json()["candidate"]
    assert patched["editable_spec"]["parameters"]["body_length"] == 188
    assert patched["editable_spec"]["parameters"]["port_diameter"] == 52
    assert patched["editable_spec"]["component_keys"] == ["pump.casing", "pump.mechanical_seal", "pump.shaft"]
    assert patched["status"] == "needs_review"
    assert "人工修正泵体长度" in patched["review_notes"]

    rendered = client.post(f"/api/cad/candidates/{candidate['id']}/render")
    assert rendered.status_code == 200
    assert rendered.json()["candidate"]["artifact_manifest"]["cad_files"]["glb"]["exists"] is True


def test_approved_candidate_can_be_promoted_to_cad_workbench_model() -> None:
    candidate = _create_candidate()
    candidate_id = candidate["id"]
    reviewed = client.post(
        f"/api/cad/candidates/{candidate_id}/review",
        json={"status": "approved_candidate", "reviewer": "ME-R2", "notes": "审核通过，可作为候选结构链资产。"},
    )
    assert reviewed.status_code == 200

    response = client.post(
        f"/api/cad/candidates/{candidate_id}/promote",
        json={"model_title": "ISG80-160 泵密封区候选 CAD", "component_binding_mode": "candidate_component_key"},
    )
    assert response.status_code == 200
    promotion = response.json()["promotion"]
    assert promotion["status"] == "promoted_standard_candidate"
    assert promotion["model_id"].startswith("candidate-cad-")

    models = client.get("/api/3d/models?equipment=pump").json()["models"]
    assert any(item["id"] == promotion["model_id"] for item in models)


def test_candidate_cad_file_roles_are_accessible() -> None:
    candidate = _create_candidate()
    roles = ["step", "stl", "glb", "render-iso", "comparison", "artifact-manifest"]
    if candidate["runtime_report"].get("artifact_mode") == "real_render":
        roles += ["openscad-stl", "freecad-validation", "openscad-report", "blender-report"]
    for role in roles:
        response = client.get(f"/api/cad/candidates/{candidate['id']}/files/{role}")
        assert response.status_code == 200, role
        assert response.content
