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

from backend.app.main import app  # noqa: E402


client = TestClient(app)


def test_part_tree_candidate_api_reports_verified_pool_without_overclaiming() -> None:
    response = client.get("/api/3d/part-tree-candidates")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] >= 8
    assert payload["summary"]["passed"] >= 8
    assert payload["summary"]["assembly_tree"] == 0
    assert payload["summary"]["multi_solid_or_feature_tree"] >= 8
    assert payload["truth_statement"].startswith("未找到原生装配树")
    assert payload["candidates"]
    assert {item["equipment"] for item in payload["candidates"]} >= {"bearing", "motor", "pump", "engine"}
    assert all(item["status"] == "passed" for item in payload["candidates"])
    assert all(item["source_url"].startswith("https://") for item in payload["candidates"])
    assert any(item["analysis"]["classification"] == "multi_solid_cad" for item in payload["candidates"])
    assert any(item["analysis"]["classification"] == "freecad_feature_tree" for item in payload["candidates"])
    assert any(item["warnings"] for item in payload["candidates"])


def test_frontend_exposes_part_tree_candidate_workbench() -> None:
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "零件树候选资源" in index
    assert "原生装配树" in index
    assert "partTreeCandidate" in app_js
    assert "/api/3d/part-tree-candidates" in app_js
