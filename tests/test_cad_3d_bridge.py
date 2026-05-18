from __future__ import annotations

import os
import sys
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


def test_standard_model_exposes_cad_3d_bridge() -> None:
    response = client.get("/api/3d/models/freecad_6201_2rs_bearing")

    assert response.status_code == 200
    body = response.json()
    bridge = body["cad_bridge"]
    assert bridge["title"] == "CAD-3D 双证据链"
    assert bridge["cad_source"]["path"].endswith("6201-2RS_Ball_Bearing.step")
    assert bridge["cad_source"]["preview_url"].endswith("/api/3d/models/freecad_6201_2rs_bearing/files/source-cad/preview")
    assert bridge["cad_source"]["download_url"].endswith("/api/3d/models/freecad_6201_2rs_bearing/files/source-cad")
    assert bridge["cad_source"]["exists"] is True
    assert bridge["cad_source"]["sha256"]
    assert bridge["glb_viewer"]["path"].endswith("6201-2RS_Ball_Bearing.glb")
    assert bridge["glb_viewer"]["public_url"].endswith(".glb")
    assert bridge["glb_viewer"]["preview_url"].endswith("/api/3d/models/freecad_6201_2rs_bearing/files/glb/preview")
    assert bridge["glb_viewer"]["download_url"].endswith("/api/3d/models/freecad_6201_2rs_bearing/files/glb")
    assert bridge["glb_viewer"]["exists"] is True
    assert bridge["sidecar"]["path"].endswith("6201-2RS_Ball_Bearing.sidecar.json")
    assert bridge["sidecar"]["preview_url"].endswith("/api/3d/models/freecad_6201_2rs_bearing/files/sidecar/preview")
    assert bridge["sidecar"]["download_url"].endswith("/api/3d/models/freecad_6201_2rs_bearing/files/sidecar")
    assert bridge["sidecar"]["exists"] is True
    assert bridge["sidecar"]["component_count"] >= 5
    assert bridge["conversion"]["path"].endswith("conversion_report.json")
    assert bridge["conversion"]["preview_url"].endswith("/api/3d/models/freecad_6201_2rs_bearing/files/conversion-report/preview")
    assert bridge["conversion"]["download_url"].endswith("/api/3d/models/freecad_6201_2rs_bearing/files/conversion-report")
    assert bridge["conversion"]["exists"] is True
    assert bridge["conversion"]["toolchain"]["cad_import"]
    assert [item["stage"] for item in bridge["trace_chain"]] == [
        "source_cad",
        "mesh_conversion",
        "semantic_sidecar",
        "sop_binding",
    ]
    assert any(item["component_key"] == "outer_ring" for item in bridge["component_bindings"])
    assert bridge["limitations"]

    source_cad = client.get(bridge["cad_source"]["download_url"])
    assert source_cad.status_code == 200
    assert b"ISO-10303-21" in source_cad.content[:200]

    glb = client.get(bridge["glb_viewer"]["download_url"])
    assert glb.status_code == 200
    assert glb.content[:4] == b"glTF"

    sidecar = client.get(bridge["sidecar"]["download_url"])
    assert sidecar.status_code == 200
    assert sidecar.json()["asset_id"] == "freecad_6201_2rs_bearing"

    conversion = client.get(bridge["conversion"]["download_url"])
    assert conversion.status_code == 200
    assert conversion.json()["asset_id"] == "freecad_6201_2rs_bearing"

    cad_preview = client.get(bridge["cad_source"]["preview_url"])
    assert cad_preview.status_code == 200
    assert "text/html" in cad_preview.headers["content-type"]
    assert "CAD 原件预览" in cad_preview.text
    assert "ISO-10303-21" in cad_preview.text
    assert bridge["cad_source"]["download_url"] in cad_preview.text

    glb_preview = client.get(bridge["glb_viewer"]["preview_url"])
    assert glb_preview.status_code == 200
    assert "GLB 网页模型预览" in glb_preview.text
    assert bridge["glb_viewer"]["download_url"] in glb_preview.text


def test_spatial_guidance_carries_cad_3d_bridge() -> None:
    response = client.post(
        "/api/3d/guidance",
        json={
            "text": "轴承外圈滚道磨损并伴随异响，需要拆检定位。",
            "equipment": "bearing",
            "model": "6201-2RS",
            "sop_steps": ["断电挂牌后检查外圈滚道。"],
            "compliance": [{"code": "LOTO", "label": "断电挂牌", "passed": True, "evidence": "已确认"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cad_bridge"]["cad_source"]["format"] == "STEP"
    assert body["cad_bridge"]["glb_viewer"]["format"] == "GLB"
    assert body["cad_bridge"]["sidecar"]["binding_mode"] == "named_glb_node_with_semantic_hotspots"
    assert any(item["sop_step_count"] >= 1 for item in body["cad_bridge"]["component_bindings"])


def test_frontend_renders_cad_3d_bridge_panel() -> None:
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "CAD-3D 双证据" in index
    assert "CAD 原件" in index
    assert "网页 GLB" in index
    assert "sidecar 标注" in index
    assert "打开 CAD" in index
    assert "打开 GLB" in index
    assert "打开 sidecar" in index
    assert "转换报告" in index
    assert ".preview_url" in index
    assert "cadBridge" in app_js
    assert "bridgeComponentBindings" in app_js
