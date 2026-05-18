from __future__ import annotations

import sys
import os
import csv
import json
import re
import subprocess
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["ACTIVE_MODEL_PROVIDER"] = "local"
os.environ["TEXT_AGENT_PROVIDER"] = "local"
os.environ["VISION_AGENT_PROVIDER"] = "local"
os.environ["EMBEDDING_AGENT_PROVIDER"] = "local"
os.environ["COMPLIANCE_AGENT_PROVIDER"] = "local"
os.environ["KNOWLEDGE_AGENT_PROVIDER"] = "local"
os.environ["A1_DB_PATH"] = str(ROOT / "data" / "test-maintenance.db")

from backend.app.database import reset_demo_db  # noqa: E402
from backend.app.main import app  # noqa: E402


def setup_module() -> None:
    reset_demo_db()


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_favicon_does_not_404() -> None:
    response = client.get("/favicon.ico")
    assert response.status_code in {200, 204}


def test_query_returns_sop_citations_and_compliance() -> None:
    response = client.post(
        "/api/query",
        json={
            "text": "电机端盖温度升高，伴随低频振动和轴承异响",
            "equipment": "motor",
            "model": "Y2-160M",
            "maintenance_level": "二级检修",
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citations"]
    assert body["sop_steps"]
    assert any(item["code"] == "LOTO" for item in body["compliance"])
    assert body["agents"]
    assert body["graph_paths"]
    assert "visual_evidence" in body
    assert body["resource_verification_summary"]["summary"]["critical_failures"] == []
    assert body["model_review"]["text"]
    assert body["model_review"]["provider"] in {"local", "openai", "opencode", "codex", "spatialai"}


def test_query_returns_structured_agent_trace() -> None:
    response = client.post(
        "/api/query",
        json={
            "text": "电机轴承温升并伴随低频振动，要求生成可追溯检修流程",
            "equipment": "motor",
            "model": "Y2-160M",
            "maintenance_level": "二级检修",
            "image_caption": "轴承端盖附近有油污，疑似润滑脂污染和密封老化",
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    body = response.json()
    agents = body["agents"]
    assert {item["id"] for item in agents} >= {
        "vision",
        "retrieval",
        "diagnosis",
        "sop",
        "compliance",
        "knowledge_update",
    }
    for item in agents:
        assert {"id", "agent", "status", "input", "output", "evidence", "confidence", "duration_ms", "next_action"} <= set(item)
        assert 0 <= item["confidence"] <= 1
        assert item["duration_ms"] >= 0
    retrieval = next(item for item in agents if item["id"] == "retrieval")
    assert retrieval["evidence"]["manual_hits"] == len(body["citations"])
    assert retrieval["evidence"]["case_hits"] == len(body["similar_cases"])
    knowledge = next(item for item in agents if item["id"] == "knowledge_update")
    assert knowledge["status"] in {"ready", "pending_review"}


def test_query_returns_integrated_workflow_state() -> None:
    response = client.post(
        "/api/query",
        json={
            "text": "离心泵机械密封连续滴漏，密封端有泄漏痕迹，需要拆检并确认安全闸门",
            "equipment": "pump",
            "model": "mini-vacuum-pump",
            "maintenance_level": "二级检修",
            "image_caption": "泵端面密封区域有液体滴漏和油污痕迹",
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    body = response.json()
    workflow = body["workflow_state"]
    assert workflow["equipment"] == "pump"
    assert workflow["task_id"].startswith("a1-")
    assert "pump.mechanical_seal" in workflow["selected_component_keys"]
    assert "pump_seal_zone" in workflow["selected_model_component_keys"]
    assert workflow["safety_gate"]["status"] in {"ready", "warning", "blocked", "needs_confirmation"}
    assert workflow["safety_gate"]["blocking_items"] == body["spatial_guidance"]["safety_gate"]["blocking_reasons"]
    assert {stage["id"] for stage in workflow["stages"]} >= {
        "vision",
        "retrieval",
        "cad_grounding",
        "sop",
        "safety_gate",
        "case_loop",
        "evaluation",
    }
    cad_stage = next(stage for stage in workflow["stages"] if stage["id"] == "cad_grounding")
    assert cad_stage["status"] in {"done", "needs_confirmation", "needs_review"}
    assert cad_stage["evidence_refs"]


def test_query_returns_tri_mro_alignment_contract() -> None:
    response = client.post(
        "/api/query",
        json={
            "text": "离心泵机械密封持续滴漏，现场人员想直接拆泵端盖，需要判断是否可以放行拆检。",
            "equipment": "pump",
            "model": "mini-vacuum-pump",
            "maintenance_level": "三级检修",
            "image_caption": "泵机械密封区域有液体滴漏，端盖附近有油污和残液痕迹",
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    body = response.json()
    alignment = body["tri_mro_alignment"]
    assert alignment["framework"] == "Tri-MRO"
    assert alignment["alignment_status"] in {"complete", "partial", "blocked", "needs_review"}
    assert alignment["claim"]["text"] == body["diagnosis"]
    assert alignment["claim"]["traceability"]["evidence_count"] == len(alignment["evidence_chain"])
    assert alignment["claim"]["traceability"]["operation_step_count"] == len(alignment["operation_chain"])
    assert alignment["evidence_chain"]
    assert alignment["evidence_chain"][0]["source_type"] in {"manual", "case", "graph", "visual"}
    assert alignment["structure_chain"]["equipment"] == "pump"
    assert "pump.mechanical_seal" in alignment["structure_chain"]["component_keys"]
    assert alignment["structure_chain"]["cad_model_id"] == body["spatial_guidance"]["model_id"]
    assert alignment["operation_chain"]
    assert alignment["operation_chain"][0]["component_key"]
    assert alignment["safety_gate"]["status"] in {"ready", "warning", "blocked", "needs_confirmation"}
    assert "作业票" in alignment["knowledge_governance"]["work_order_lifecycle"]
    assert alignment["metrics"]["tri_chain_coverage"] >= 0


def test_component_taxonomy_maps_legacy_3d_keys_to_canonical_keys() -> None:
    from backend.app.component_taxonomy import canonical_component_key, component_confidence_status

    assert canonical_component_key("pump", "pump_seal_zone") == "pump.mechanical_seal"
    assert canonical_component_key("motor", "front_bearing_end") == "motor.bearing"
    assert canonical_component_key("engine", "cooling_fins") == "engine.cylinder_head"
    assert canonical_component_key("bearing", "rolling_elements") == "bearing.rolling_elements"
    assert component_confidence_status(0.72) == "done"
    assert component_confidence_status(0.48) == "needs_confirmation"
    assert component_confidence_status(0.2) == "needs_review"


def test_upload_image_creates_structured_visual_asset(tmp_path: Path) -> None:
    image_path = ROOT / "data" / "image_eval" / "images" / "bearing_spalling_01.jpg"
    if not image_path.exists():
        image_path = next((ROOT / "data" / "image_eval" / "images").glob("*.jpg"))

    with image_path.open("rb") as handle:
        response = client.post(
            "/api/upload-image",
            files={"file": ("bearing_spalling_01.jpg", handle, "image/jpeg")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["visual_asset_id"] > 0
    assert body["visual_analysis"]["equipment_candidates"]
    assert body["visual_analysis"]["component_candidates"]
    assert body["visual_analysis"]["defect_labels"]
    assert "ocr_text" in body["visual_analysis"]
    assert "flowchart" in body["visual_analysis"]

    listed = client.get("/api/visual-assets")
    assert listed.status_code == 200
    assets = listed.json()["assets"]
    assert any(item["id"] == body["visual_asset_id"] for item in assets)


def test_candidate_cad_asset_pipeline_from_visual_asset() -> None:
    image_path = ROOT / "data" / "image_eval" / "images" / "pump_mechanical_seal_parts_02.jpg"
    if not image_path.exists():
        image_path = next((ROOT / "data" / "image_eval" / "images").glob("*.jpg"))

    with image_path.open("rb") as handle:
        uploaded = client.post(
            "/api/upload-image",
            files={"file": (image_path.name, handle, "image/jpeg")},
        ).json()

    response = client.post(
        "/api/cad/candidates/from-visual",
        json={
            "visual_asset_id": uploaded["visual_asset_id"],
            "equipment": "pump",
            "model": "ISG80-160",
            "generator": "cadquery_openscad",
        },
    )

    assert response.status_code == 200
    body = response.json()
    candidate = body["candidate"]
    assert candidate["id"] > 0
    assert candidate["equipment"] == "pump"
    assert candidate["status"] == "needs_review"
    assert candidate["risk_boundary"]["not_for_measurement"] is True
    assert candidate["observation"]["visual_asset_id"] == uploaded["visual_asset_id"]
    assert candidate["cad_spec"]["equipment"] == "pump"
    assert candidate["cad_spec"]["component_keys"]
    assert "pump.mechanical_seal" in candidate["cad_spec"]["component_keys"]
    assert candidate["code_artifacts"]["cadquery"].endswith(".py")
    assert candidate["code_artifacts"]["openscad"].endswith(".scad")
    assert candidate["render_artifacts"]["preview_svg"].endswith(".svg")
    assert candidate["vlm_compare"]["status"] in {"pass", "needs_review", "reject"}
    assert candidate["review_gate"]["required"] is True

    listed = client.get("/api/cad/candidates?status=needs_review")
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["summary"]["needs_review"] >= 1
    assert any(item["id"] == candidate["id"] for item in listed_body["candidates"])

    preview = client.get(f"/api/cad/candidates/{candidate['id']}/files/preview")
    assert preview.status_code == 200
    assert b"<svg" in preview.content[:200]

    reviewed = client.post(
        f"/api/cad/candidates/{candidate['id']}/review",
        json={
            "status": "approved_candidate",
            "reviewer": "ME-R2",
            "notes": "孔位和密封区相对位置可用于结构链演示，不作为测量依据。",
        },
    )
    assert reviewed.status_code == 200
    reviewed_candidate = reviewed.json()["candidate"]
    assert reviewed_candidate["status"] == "approved_candidate"
    assert reviewed_candidate["reviewer"] == "ME-R2"
    assert reviewed_candidate["review_notes"]


def test_query_uses_visual_asset_structured_analysis() -> None:
    image_path = ROOT / "data" / "image_eval" / "images" / "bearing_spalling_01.jpg"
    if not image_path.exists():
        image_path = next((ROOT / "data" / "image_eval" / "images").glob("*.jpg"))

    with image_path.open("rb") as handle:
        uploaded = client.post(
            "/api/upload-image",
            files={"file": ("bearing_spalling_01.jpg", handle, "image/jpeg")},
        ).json()

    response = client.post(
        "/api/query",
        json={
            "text": "结合上传图片判断轴承故障并生成检修步骤",
            "equipment": "bearing",
            "model": "6205-2RS",
            "maintenance_level": "二级检修",
            "visual_asset_id": uploaded["visual_asset_id"],
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["visual_analysis"]["id"] == uploaded["visual_asset_id"]
    assert body["visual_analysis"]["defect_labels"]
    assert any(item["type"] == "uploaded_visual_asset" for item in body["visual_evidence"])
    assert body["agents"][0]["evidence"]["has_structured_visual_asset"] is True
    assert body["spatial_guidance"]["mode"] == "standard_3d_guidance"
    assert body["spatial_guidance"]["highlighted_components"]


def test_3d_models_guidance_and_reconstruction_jobs() -> None:
    bearing_models = client.get("/api/3d/models?equipment=bearing")
    assert bearing_models.status_code == 200
    bearing_model_list = bearing_models.json()["models"]
    assert bearing_model_list
    assert bearing_model_list[0]["id"] == "freecad_6201_2rs_bearing"
    assert bearing_model_list[0]["viewer_mode"] == "local_glb"
    assert bearing_model_list[0]["processed_mesh_url"].endswith(".glb")
    assert bearing_model_list[0]["license"]["id"] == "CC-BY-3.0"

    bearing_model = client.get("/api/3d/models/freecad_6201_2rs_bearing")
    assert bearing_model.status_code == 200
    bearing_body = bearing_model.json()
    assert bearing_body["source_type"] == "authorized_cad"
    assert bearing_body["viewer_mode"] == "local_glb"
    assert bearing_body["mesh_path"].startswith("/3d-assets/authorized/")
    assert bearing_body["source_cad_path"].endswith("6201-2RS_Ball_Bearing.step")
    assert bearing_body["sidecar_path"].endswith("6201-2RS_Ball_Bearing.sidecar.json")
    assert {"outer_ring", "rolling_elements"} <= {component["component_key"] for component in bearing_body["components"]}

    glb_response = client.get(bearing_body["mesh_path"])
    assert glb_response.status_code == 200
    assert glb_response.content[:4] == b"glTF"

    bearing_guidance = client.post(
        "/api/3d/guidance",
        json={
            "text": "轴承运行异响，外圈滚道磨损并疑似剥落",
            "equipment": "bearing",
            "model": "6201-2RS",
            "sop_steps": [],
            "compliance": [{"code": "LOTO", "label": "断电挂牌", "passed": True, "evidence": "已确认"}],
        },
    )
    assert bearing_guidance.status_code == 200
    bearing_guidance_body = bearing_guidance.json()
    assert bearing_guidance_body["model_id"] == "freecad_6201_2rs_bearing"
    assert bearing_guidance_body["viewer_mode"] == "local_glb"
    assert bearing_guidance_body["scene_state"]["viewer_mode"] == "local_glb"
    assert bearing_guidance_body["scene_state"]["section"]["enabled"] is True
    assert bearing_guidance_body["scene_state"]["binding_quality"]["object_level_binding"] is False
    assert bearing_guidance_body["scene_state"]["active_component_key"] in {"outer_ring", "rolling_elements"}
    assert bearing_guidance_body["highlighted_components"][0]["component_key"] in {"outer_ring", "rolling_elements"}
    assert bearing_guidance_body["sop_bindings"]
    assert bearing_guidance_body["sop_bindings"][0]["phase"] == "安全确认"
    assert bearing_guidance_body["sop_bindings"][0]["component_label"]
    assert bearing_guidance_body["model_maturity"]["level"] == "v1_authorized_semantic"
    assert bearing_guidance_body["binding_quality"]["binding_mode"] == "named_glb_node_with_semantic_hotspots"
    assert bearing_guidance_body["professional_gaps"]
    assert bearing_guidance_body["safety_gate"]["status"] == "ready"

    pending_gate = client.post(
        "/api/3d/guidance",
        json={
            "text": "轴承外圈滚道有剥落，但还没完成断电挂牌",
            "equipment": "bearing",
            "model": "6201-2RS",
            "sop_steps": [],
            "compliance": [],
        },
    )
    assert pending_gate.status_code == 200
    pending_body = pending_gate.json()
    assert pending_body["safety_gate"]["status"] == "needs_confirmation"
    assert len(pending_body["safety_gate"]["required_checks"]) >= 5
    assert "断电挂牌" in pending_body["safety_gate"]["blocking_reasons"]

    models = client.get("/api/3d/models?equipment=pump")
    assert models.status_code == 200
    model_list = models.json()["models"]
    assert model_list
    model_id = model_list[0]["id"]

    model = client.get(f"/api/3d/models/{model_id}")
    assert model.status_code == 200
    model_body = model.json()
    assert model_body["equipment"] == "pump"
    assert model_body["id"] == "freecad_mini_vacuum_pump"
    assert model_body["source_type"] == "authorized_cad"
    assert model_body["viewer_mode"] == "local_glb"
    assert model_body["mesh_path"].startswith("/3d-assets/authorized/")
    assert model_body["license"]["id"] == "CC-BY-3.0"
    assert model_body["node_bindings"]["object_level_binding"] is True
    assert any(component["component_key"] == "pump_seal_zone" for component in model_body["components"])

    guidance = client.post(
        "/api/3d/guidance",
        json={
            "text": "离心泵机械密封泄漏，密封处连续滴漏",
            "equipment": "pump",
            "model": "ISG80-160",
            "sop_steps": ["断电挂牌并关闭进出口阀", "泄压排液后检查机械密封动静环"],
            "compliance": [{"code": "LOTO", "label": "断电挂牌", "passed": True, "evidence": "已确认"}],
        },
    )
    assert guidance.status_code == 200
    guidance_body = guidance.json()
    assert guidance_body["model_id"] == "freecad_mini_vacuum_pump"
    assert guidance_body["source_type"] == "authorized_cad"
    assert guidance_body["viewer_mode"] == "local_glb"
    assert guidance_body["model_maturity"]["object_level_binding"] is True
    assert guidance_body["highlighted_components"][0]["component_key"] == "pump_seal_zone"
    assert guidance_body["safety_gate"]["status"] == "ready"

    image_path = ROOT / "data" / "image_eval" / "images" / "pump_mechanical_seal_parts_02.jpg"
    if not image_path.exists():
        image_path = next((ROOT / "data" / "image_eval" / "images").glob("*.jpg"))
    with image_path.open("rb") as handle:
        uploaded = client.post(
            "/api/upload-image",
            files={"file": ("pump_mechanical_seal_parts_02.jpg", handle, "image/jpeg")},
        ).json()

    one_photo = client.post(
        "/api/3d/reconstruct/one-photo",
        json={"visual_asset_id": uploaded["visual_asset_id"], "provider": "cached_demo"},
    )
    assert one_photo.status_code == 200
    one_photo_job = one_photo.json()["job"]
    assert one_photo_job["mode"] == "one_photo"
    assert one_photo_job["status"] == "completed_cached"
    assert "尺寸测量" in one_photo_job["limitations"]
    assert one_photo_job["log"]["algorithm_status"] == "standard_model_alignment_only"
    assert one_photo_job["log"]["is_true_3d_generation"] is False
    assert "映射到授权标准 CAD/GLB" in one_photo_job["log"]["pipeline_steps"][2]

    image_bytes = image_path.read_bytes()
    multi_photo = client.post(
        "/api/3d/reconstruct/multi-photo?equipment=pump",
        files=[
            ("files", ("view-01.jpg", image_bytes, "image/jpeg")),
            ("files", ("view-02.jpg", image_bytes, "image/jpeg")),
        ],
    )
    assert multi_photo.status_code == 200
    multi_photo_job = multi_photo.json()["job"]
    assert multi_photo_job["mode"] == "multi_photo"
    assert multi_photo_job["status"] == "blocked_quality_gate"
    assert multi_photo_job["log"]["algorithm_status"] == "blocked_quality_gate"
    assert multi_photo_job["log"]["is_true_3d_generation"] is False
    assert multi_photo_job["log"]["quality_gate"]["passed"] is False
    assert "COLMAP" in multi_photo_job["log"]["planned_backends"]
    assert "scripts/run_3d_reconstruction.py" in multi_photo_job["log"]["runner_command"]

    fetched_job = client.get(f"/api/3d/jobs/{one_photo_job['id']}")
    assert fetched_job.status_code == 200
    assert fetched_job.json()["job"]["id"] == one_photo_job["id"]


def test_photo_to_3d_runner_dry_run_package(tmp_path: Path) -> None:
    photo_dir = tmp_path / "photos"
    output_dir = tmp_path / "package"
    photo_dir.mkdir()
    for index in range(3):
        (photo_dir / f"view-{index + 1:02d}.jpg").write_bytes(b"demo")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_3d_reconstruction.py"),
            "--job-id",
            "test-job",
            "--input-dir",
            str(photo_dir),
            "--output-dir",
            str(output_dir),
            "--backend",
            "dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    plan_path = output_dir / "photo_to_3d_plan.json"
    assert plan_path.exists()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["status"] == "blocked_quality_gate"
    assert plan["true_3d_generation"] is False
    assert "COLMAP SfM/MVS" in plan["planned_backends"]
    assert any("dry-run" in item for item in plan["warnings"])
    assert (output_dir / "run_commands.ps1").exists()


def test_authorized_motor_pump_and_engine_assets_are_local_glb() -> None:
    manifest_path = ROOT / "data" / "3d" / "authorized_models" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    resources = {resource["id"]: resource for resource in manifest["resources"]}
    assert {
        "freecad_nema23_stepper_motor",
        "freecad_mini_vacuum_pump",
        "artec_motorcycle_engine_hd",
    } <= set(resources)

    for asset_id, equipment, model_code in [
        ("freecad_nema23_stepper_motor", "motor", "NEMA-23"),
        ("freecad_mini_vacuum_pump", "pump", "mini-vacuum-pump"),
        ("artec_motorcycle_engine_hd", "engine", "motorcycle-engine-hd"),
    ]:
        resource = resources[asset_id]
        assert resource["equipment"] == equipment
        assert resource["model_code"] == model_code
        assert resource["viewer_mode"] == "local_glb"
        assert resource["license"] == "CC-BY-3.0"
        assert resource["node_bindings"]["binding_mode"] == "named_glb_node_with_semantic_hotspots"
        assert resource["node_bindings"]["object_level_binding"] is True
        assert resource["node_bindings"]["exact_cad_face_binding"] is False
        assert (ROOT / resource["processed_mesh_path"]).exists()
        assert (ROOT / resource["sidecar_path"]).exists()

    blocked_path = ROOT / "data" / "3d" / "authorized_models" / "blocked_candidates.json"
    blocked = json.loads(blocked_path.read_text(encoding="utf-8"))
    engine_block = next(item for item in blocked["blocked_candidates"] if item["equipment"] == "engine")
    assert engine_block["status"] == "resolved_with_mesh_model"
    assert engine_block["resolved_by"] == "artec_motorcycle_engine_hd"


def test_3d_component_identifiers_use_canonical_keys_with_domain_aliases() -> None:
    def sidecar(asset_id: str, filename: str) -> dict:
        path = ROOT / "data" / "3d" / "authorized_models" / asset_id / filename
        return json.loads(path.read_text(encoding="utf-8"))

    pump = sidecar("freecad_mini_vacuum_pump", "Mini_vacuum_pump.sidecar.json")
    pump_keys = {item["id"] for item in pump["part_semantics"]}
    assert "mechanical_seal" not in pump_keys
    pump_seal = next(item for item in pump["part_semantics"] if item["id"] == "pump_seal_zone")
    assert "mechanical_seal" in pump_seal["aliases"]
    assert "机械密封" in pump_seal["manual_keywords"]
    assert pump["node_bindings"]["pump_seal_zone"]["node"].endswith("__pump_seal_zone_marker")

    engine = sidecar("artec_motorcycle_engine_hd", "Motorcycle_engine_HD.sidecar.json")
    engine_keys = {item["id"] for item in engine["part_semantics"]}
    assert "radiator" not in engine_keys
    cooling = next(item for item in engine["part_semantics"] if item["id"] == "cooling_fins")
    assert {"radiator", "cooling_assembly"} <= set(cooling["aliases"])
    assert "冷却" in cooling["manual_keywords"]
    assert engine["node_bindings"]["cooling_fins"]["node"].endswith("__cooling_fins_marker")

    from backend.app.spatial_guidance import _default_component_keys

    for equipment, keys in {
        "motor": {"front_bearing_end", "end_cover"},
        "pump": {"pump_seal_zone", "pump_shaft"},
        "engine": {"spark_plug", "cylinder_head", "cylinder_block"},
    }.items():
        assert set(_default_component_keys(equipment)) <= keys


def test_semantic_sidecars_cover_motor_pump_and_engine() -> None:
    expected = {
        "motor": {
            "label": "前端轴承端",
            "query": "电机端盖温升伴随轴承异响和低频振动",
            "component": "front_bearing_end",
            "viewer_mode": "local_glb",
            "maturity": "v1_authorized_semantic",
            "model_id": "freecad_nema23_stepper_motor",
        },
        "pump": {
            "label": "泵头密封区",
            "query": "离心泵机械密封连续滴漏，密封端有泄漏痕迹",
            "component": "pump_seal_zone",
            "viewer_mode": "local_glb",
            "maturity": "v1_authorized_semantic",
            "model_id": "freecad_mini_vacuum_pump",
        },
        "engine": {
            "label": "火花塞",
            "query": "发动机火花塞积碳，冷车起动困难，需要检查间隙",
            "component": "spark_plug",
            "viewer_mode": "local_glb",
            "maturity": "v1_authorized_semantic",
            "model_id": "artec_motorcycle_engine_hd",
        },
    }
    for equipment, spec in expected.items():
        models = client.get(f"/api/3d/models?equipment={equipment}")
        assert models.status_code == 200
        model_id = models.json()["models"][0]["id"]
        assert model_id == spec["model_id"]
        model = client.get(f"/api/3d/models/{model_id}")
        assert model.status_code == 200
        model_body = model.json()
        assert model_body["viewer_mode"] == spec["viewer_mode"]
        if spec["viewer_mode"] == "local_glb":
            assert model_body["source_type"] == "authorized_cad"
            assert model_body["mesh_path"].startswith("/3d-assets/authorized/")
            assert model_body["license"]["id"] == "CC-BY-3.0"
            assert model_body["node_bindings"]["object_level_binding"] is True
        else:
            assert model_body["sidecar_path"].endswith(f"{model_id}.sidecar.json")
            assert model_body["node_bindings"]["semantic_sidecar_ready"] is True
            assert any("语义 sidecar" in item for item in model_body["limitations"])
        assert spec["label"] in {component["label"] for component in model_body["components"]}

        guidance = client.post(
            "/api/3d/guidance",
            json={
                "text": spec["query"],
                "equipment": equipment,
                "model": model_body["model_code"],
                "sop_steps": [],
                "compliance": [],
            },
        )
        assert guidance.status_code == 200
        guidance_body = guidance.json()
        assert guidance_body["viewer_mode"] == spec["viewer_mode"]
        assert guidance_body["model_maturity"]["level"] == spec["maturity"]
        assert guidance_body["highlighted_components"][0]["component_key"] == spec["component"]
        assert guidance_body["inspection_views"]


def test_manifest_visual_assets_are_cached_and_traceable() -> None:
    response = client.get("/api/visual-assets?limit=60")
    assert response.status_code == 200
    assets = response.json()["assets"]
    approved = [asset for asset in assets if asset["review_status"] == "approved"]
    assert len(approved) >= 30
    assert {asset["equipment"] for asset in approved} >= {"motor", "pump", "bearing"}
    for asset in approved[:10]:
        assert asset["manifest_id"].startswith("IMG-")
        assert asset["source_url"].startswith("https://commons.wikimedia.org/")
        assert asset["license_note"]
        assert asset["width"] > 0
        assert asset["height"] > 0
        assert len(asset["sha256"]) == 64
        assert asset["analysis"]["provider"] == "cached_manifest"

    query = client.post(
        "/api/query",
        json={
            "text": "结合已审核图片判断轴承滚道损伤并生成检修步骤",
            "equipment": "bearing",
            "model": "6205-2RS",
            "maintenance_level": "二级检修",
            "visual_asset_id": approved[0]["id"],
            "top_k": 6,
        },
    )
    assert query.status_code == 200
    body = query.json()
    assert body["visual_analysis"]["review"]["status"] == "approved"
    assert any(item["type"] == "uploaded_visual_asset" for item in body["visual_evidence"])


def test_official_engine_manual_ingestion_and_query() -> None:
    source_pdf = ROOT / "data" / "raw" / "manuals" / "official" / "motorcycle-engine-maintenance-manual.pdf"
    assert source_pdf.exists()

    ingested = client.post("/api/admin/ingest-manuals?rebuild=false")
    assert ingested.status_code == 200
    docs = ingested.json()["documents"]
    assert any(item["equipment"] == "engine" for item in docs)

    response = client.post(
        "/api/query",
        json={
            "text": "摩托车发动机火花塞间隙如何检查，压缩压力偏低如何判断？",
            "equipment": "engine",
            "model": "摩托车发动机",
            "maintenance_level": "二级检修",
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citations"]
    assert any("motorcycle-engine-maintenance-manual" in item["source"] for item in body["citations"])
    assert any("火花塞" in step or "压缩压力" in step for step in body["sop_steps"])
    assert body["graph_paths"]


def test_case_approval_updates_graph() -> None:
    created = client.post(
        "/api/cases",
        json={
            "title": "测试案例：泵机械密封泄漏",
            "equipment": "pump",
            "model": "ISG80-160",
            "symptoms": "密封处有连续滴漏",
            "fault_type": "泄漏",
            "cause": "O 形圈老化",
            "actions": "隔离泄压后更换密封组件",
            "parts": "机械密封组件",
            "risk_level": "high",
        },
    )
    assert created.status_code == 200
    case_id = created.json()["id"]
    approved = client.post(f"/api/cases/{case_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    graph = client.get("/api/knowledge-graph").json()
    assert any(node["id"] == f"case_{case_id}" for node in graph["nodes"])


def test_feedback_roundtrip_and_query_hints() -> None:
    created = client.post(
        "/api/feedback",
        json={
            "question": "电机轴承温升并伴随低频振动",
            "original_answer": "只建议补充润滑脂。",
            "corrected_answer": "必须先断电挂牌，复测振动频谱，再拆检轴承游隙和润滑污染。",
            "notes": "原答案漏掉 LOTO 和复测。",
        },
    )
    assert created.status_code == 200

    listed = client.get("/api/feedback")
    assert listed.status_code == 200
    body = listed.json()
    assert body["feedback"]
    assert "sk-" not in listed.text.lower()

    query = client.post(
        "/api/query",
        json={
            "text": "电机轴承温升，低频振动明显",
            "equipment": "motor",
            "model": "Y2-160M",
            "maintenance_level": "二级检修",
            "top_k": 6,
        },
    )
    assert query.status_code == 200
    assert query.json()["feedback_hints"]


def test_provider_report_redacts_keys() -> None:
    response = client.get("/api/providers")
    assert response.status_code == 200
    text = response.text.lower()
    assert "sk-" not in text

    routing = client.get("/api/agent-routing")
    assert routing.status_code == 200
    routes = routing.json()["routes"]
    assert {route["role"] for route in routes} >= {"text", "vision", "embedding", "compliance", "knowledge"}
    assert "sk-" not in routing.text.lower()


def test_graph_status_rebuild_and_query_paths_use_graph_backend() -> None:
    status = client.get("/api/graph/status")
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["backend"] in {"sqlite", "neo4j", "sqlite_fallback"}
    assert "connected" in status_body
    assert "node_count" in status_body
    assert "edge_count" in status_body

    rebuilt = client.post("/api/admin/graph/rebuild")
    assert rebuilt.status_code == 200
    rebuild_body = rebuilt.json()
    assert rebuild_body["backend"] in {"sqlite", "neo4j", "sqlite_fallback"}
    assert rebuild_body["node_count"] >= 1
    assert rebuild_body["edge_count"] >= 1

    response = client.post(
        "/api/query",
        json={
            "text": "离心泵机械密封泄漏如何检修",
            "equipment": "pump",
            "model": "ISG80-160",
            "maintenance_level": "二级检修",
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["graph_backend"] in {"sqlite", "neo4j", "sqlite_fallback"}
    assert body["graph_paths"]
    first = body["graph_paths"][0]
    assert {"path", "nodes", "edges", "source_title", "confidence"} <= set(first)


def test_public_source_manifest_covers_target_equipment() -> None:
    import json

    manifest = ROOT / "data" / "sources" / "public_manual_sources.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    sources = [source for source in payload["sources"] if source.get("active", True)]
    assert len(sources) >= 8
    assert {source["equipment"] for source in sources} >= {"motor", "pump", "bearing"}
    for source in sources:
        assert source["id"]
        assert source["source_url"].startswith("https://")
        assert source["target_filename"].endswith(".pdf")
        assert "redistribution not assumed" in source["license"]


def test_external_resource_verification_report() -> None:
    response = client.get("/api/resources/verification")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] >= 10
    assert payload["summary"]["verified"] >= 10
    assert payload["summary"]["critical_failures"] == []
    official = next(item for item in payload["resources"] if item["id"] == "official-motorcycle-engine-manual")
    assert official["verify_status"] == "verified"
    assert official["checks"]["pages"] == 41
    assert "摩托车发动机维修手册" in official["checks"]["keyword_hits"]


def test_a1_makg_hard_eval_and_work_order_samples_seeded() -> None:
    metrics = client.get("/api/metrics").json()
    hard_eval = metrics["review_status"]["eval_questions"]["total"]
    assert hard_eval >= 130
    assert metrics["review_status"]["eval_questions"]["approved"] >= 130
    assert metrics["review_status"]["cases"]["approved"] >= 150
    assert set(metrics["latest"]["category_summary"]) >= {
        "base",
        "complex",
        "image",
        "conflict",
        "no_evidence",
    }
    pending = client.get("/api/cases?status=pending").json()["cases"]
    assert any(item.get("work_order_status") == "pending_review" for item in pending)


def test_review_pack_export_has_required_columns(tmp_path) -> None:
    from scripts.export_review_pack import export_review_pack

    output_dir = tmp_path / "review"
    result = export_review_pack(review_dir=output_dir)
    assert result["cases"] >= 1
    assert result["eval_questions"] >= 1
    cases_csv = output_dir / "mechanical_cases_review.csv"
    eval_csv = output_dir / "eval_questions_review.csv"
    assert cases_csv.exists()
    assert eval_csv.exists()

    with cases_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        case_fields = set(next(csv.DictReader(handle)).keys())
    with eval_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        eval_fields = set(next(csv.DictReader(handle)).keys())

    assert {"review_status", "reviewer", "review_notes", "decision"} <= case_fields
    assert {"mechanical_accuracy_score", "sop_completeness_score", "safety_score"} <= case_fields
    assert {"review_status", "reviewer", "review_notes", "expected_reference_ok"} <= eval_fields


def test_rebuild_index_and_eval_metrics() -> None:
    rebuilt = client.post("/api/admin/rebuild-index")
    assert rebuilt.status_code == 200
    assert rebuilt.json()["manual"] >= 10

    evaluation = client.post("/api/eval/run?max_questions=4")
    assert evaluation.status_code == 200
    body = evaluation.json()
    assert body["question_count"] >= 4
    assert body["question_count"] <= body["question_total"]
    assert body["citation_coverage"] == 1.0
    assert body["review_basis"] in {"approved_only", "unreviewed_fallback"}

    metrics = client.get("/api/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["latest"]["question_count"] >= 4
    assert "category_summary" in metrics.json()["latest"]
    assert "latency_p95_ms" in metrics.json()["latest"]
    assert "review_status" in metrics.json()

    review = client.get("/api/review-status")
    assert review.status_code == 200
    assert review.json()["targets"]["approved_cases"] == 150
    assert review.json()["targets"]["approved_eval_questions"] == 130


def test_eval_comparison_runs_real_modes() -> None:
    response = client.post("/api/eval/run-comparison?max_questions=4")
    assert response.status_code == 200
    payload = response.json()
    assert payload["question_count"] == 4
    assert [item["mode"] for item in payload["benchmarks"]] == [
        "no_rag",
        "text_rag",
        "multimodal_rag",
        "full_system",
    ]
    for item in payload["benchmarks"]:
        assert item["computed"] is True
        assert item["question_count"] == 4
        assert 0 <= item["recall_at_5"] <= 1
        assert 0 <= item["citation_coverage"] <= 1
        assert 0 <= item["sop_score"] <= 1
        assert 0 <= item["hallucination_rate"] <= 1
        assert 0 <= item["safety_miss_rate"] <= 1
        assert "fallback_rate" in item
        assert "category_summary" in item

    metrics = client.get("/api/metrics")
    assert metrics.status_code == 200
    benchmarks = metrics.json()["benchmarks"]
    assert [item["mode"] for item in benchmarks] == [
        "no_rag",
        "text_rag",
        "multimodal_rag",
        "full_system",
    ]
    assert all(item["computed"] is True for item in benchmarks)


def test_frontend_exposes_agent_trace_and_comparison_controls() -> None:
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "agent-card" in index
    assert "agent.evidence" in index
    assert "agent.next_action" in index
    assert "graph_paths" in index
    assert "visual_evidence" in index
    assert "resourceVerification" in app_js
    assert "spatial-workbench" in index
    assert "安全闭环" in index
    assert "成熟度说明" in index
    assert "Photo-to-3D 当前实现状态" in index
    assert "不生成新 mesh" in index
    assert "job.log.algorithm_status" in index
    assert "activeSafetyChecks" in app_js
    assert "activeSpatialMaturity" in app_js
    assert "A1ThreeWorkbench" in (ROOT / "frontend" / "three-workbench.js").read_text(encoding="utf-8")
    assert "/api/3d/guidance" in app_js
    assert "/api/3d/reconstruct/one-photo" in app_js
    assert "/api/3d/reconstruct/multi-photo" in app_js
    assert "/api/resources/verification" in app_js
    assert "runComparison" in app_js
    assert "/api/eval/run-comparison" in app_js
    assert "category_summary" in index
    assert "approvedVisualAssetCount" in app_js


def test_submission_package_excludes_secrets_and_runtime_assets(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package

    archive = build_submission_package(output_dir=tmp_path, timestamp="20260510-0000")
    assert archive.exists()

    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())

        assert "README.md" in names
        assert ".env.example" in names
        assert "backend/app/main.py" in names
        assert "config/model_profiles.json" in names
        assert "frontend/index.html" in names
        assert "docs/DATA_SOURCES.md" in names
        assert "docs/DEPLOYMENT_LOONGARCH.md" in names
        assert "docs/DEPLOYMENT_PUBLIC.md" in names
        assert "docs/SUPABASE_SCHEMA.sql" in names
        assert "data/sources/public_manual_sources.json" in names
        assert "data/review/mechanical_cases_review.csv" in names
        assert "data/review/eval_questions_review.csv" in names
        assert "render.yaml" in names
        assert "runtime.txt" in names
        assert "SUBMISSION_MANIFEST.md" in names

        forbidden = (
            ".env",
            ".env.local",
            "data/maintenance.db",
            "data/test-maintenance.db",
        )
        assert not any(name in forbidden for name in names)
        assert not any(name.endswith(".pdf") for name in names)
        assert not any(".venv/" in name or "__pycache__/" in name or ".pytest_cache/" in name for name in names)

        text_suffixes = (".py", ".md", ".html", ".js", ".css", ".json", ".txt", ".ps1", ".csv", ".sql", ".yaml", ".example")
        for name in names:
            if name.endswith(text_suffixes):
                text = package.read(name).decode("utf-8", errors="ignore").lower()
                assert not re.search(r"sk-[a-z0-9_-]{12,}", text)


def test_readiness_audit_reports_real_evidence_and_external_gaps(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package
    from scripts.audit_readiness import run_audit, write_markdown_report

    archive = build_submission_package(output_dir=tmp_path, timestamp="20260510-audit")
    result = run_audit(submission_archive=archive)

    assert result["ready"] is False
    assert result["summary"]["manual_chunks"] >= 10
    assert result["summary"]["review_case_rows"] >= 1
    assert result["summary"]["review_eval_rows"] >= 1
    assert result["summary"]["submission_forbidden_entries"] == 0
    assert result["checks"]["web_system"]["status"] == "pass"
    assert result["checks"]["submission_package"]["status"] == "pass"
    assert result["checks"]["mechanical_review"]["status"] == "pass"
    assert result["checks"]["loongarch_runtime"]["status"] == "blocked"
    assert any("LoongArch" in item for item in result["missing_resources"])

    report = write_markdown_report(result, output_path=tmp_path / "READINESS.md")
    text = report.read_text(encoding="utf-8")
    assert "A1 Readiness Audit" in text
    assert "mechanical_review" in text
    assert "loongarch_runtime" in text


def test_readiness_audit_public_mode_does_not_block_on_loongarch(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package
    from scripts.audit_readiness import run_audit

    archive = build_submission_package(output_dir=tmp_path, timestamp="20260510-public")
    result = run_audit(submission_archive=archive, deployment_mode="public")

    assert result["deployment_mode"] == "public"
    assert result["checks"]["loongarch_runtime"]["required"] is False
    assert result["checks"]["public_demo_deployment"]["status"] == "pass"
    assert not any("LoongArch" in item for item in result["missing_resources"])


def test_review_progress_summarizes_review_csvs(tmp_path) -> None:
    from scripts.review_progress import summarize_review_dir, write_markdown_report

    review_dir = tmp_path / "review"
    review_dir.mkdir()
    cases_csv = review_dir / "mechanical_cases_review.csv"
    eval_csv = review_dir / "eval_questions_review.csv"
    cases_csv.write_text(
        "\n".join(
            [
                "id,review_status,decision,reviewer,review_notes",
                "1,approved,approve,teacher,ok",
                "2,approved,approve,teacher,ok",
                "3,needs_revision,revise,teacher,add safety item",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    eval_csv.write_text(
        "\n".join(
            [
                "id,review_status,decision,reviewer,review_notes",
                "1,approved,approve,teacher,ok",
                "2,approved,approve,teacher,ok",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = summarize_review_dir(review_dir, required_cases=2, required_eval_questions=2)
    assert result["ready_for_import"] is True
    assert result["ready_for_goal"] is True
    assert result["cases"]["approved"] == 2
    assert result["cases"]["needs_revision"] == 1
    assert result["eval_questions"]["approved"] == 2

    report = write_markdown_report(result, tmp_path / "review-status.md")
    text = report.read_text(encoding="utf-8")
    assert "Mechanical Review Progress" in text
    assert "ready_for_goal" in text


def test_build_ppt_creates_deck(tmp_path) -> None:
    from scripts.build_ppt import build_presentation

    output = build_presentation(tmp_path / "deck.pptx")
    assert output.exists()
    with zipfile.ZipFile(output) as package:
        names = package.namelist()
        assert "ppt/presentation.xml" in names
        slide_count = sum(1 for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        assert slide_count >= 10


def test_build_docx_creates_work_description(tmp_path) -> None:
    from docx import Document
    from scripts.build_docx import build_work_description_docx

    output = build_work_description_docx(output_path=tmp_path / "work-description.docx")
    assert output.exists()
    doc = Document(output)
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    assert "作品说明书" in text
    assert "赛题要求对应" in text
    assert "创新点" in text


def test_loongarch_acceptance_report_marks_current_machine_not_validated(tmp_path) -> None:
    from scripts.loongarch_acceptance import collect_acceptance, write_markdown_report

    result = collect_acceptance(api_base_url="")
    assert result["loongarch_validated"] is False
    assert result["checks"]["platform"]["status"] in {"blocked", "pass"}
    assert "machine" in result["platform"]

    report = write_markdown_report(result, tmp_path / "loongarch-acceptance.md")
    text = report.read_text(encoding="utf-8")
    assert "LoongArch Acceptance Report" in text
    assert "loongarch_validated" in text


def test_final_validation_collects_blockers(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package
    from scripts.final_validation import collect_final_validation, write_markdown_report

    archive = build_submission_package(output_dir=tmp_path, timestamp="final-validation")
    result = collect_final_validation(submission_archive=archive, api_base_url="")
    assert result["ready"] is False
    assert "mechanical_review" not in result["blockers"]
    assert "loongarch_runtime" in result["blockers"]
    assert result["submission"]["submission_forbidden_entries"] == 0

    report = write_markdown_report(result, tmp_path / "final-validation.md")
    text = report.read_text(encoding="utf-8")
    assert "Final Validation Report" in text
    assert "loongarch_runtime" in text


def test_final_validation_public_mode_skips_loongarch_blockers(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package
    from scripts.final_validation import collect_final_validation

    archive = build_submission_package(output_dir=tmp_path, timestamp="final-validation-public")
    result = collect_final_validation(
        submission_archive=archive,
        api_base_url="",
        deployment_mode="public",
    )

    assert result["deployment_mode"] == "public"
    assert "loongarch_runtime" not in result["blockers"]
    assert "loongarch_acceptance" not in result["blockers"]
    assert result["readiness"]["checks"]["public_demo_deployment"] == "pass"
