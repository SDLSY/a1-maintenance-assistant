from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["ACTIVE_MODEL_PROVIDER"] = "local"
os.environ["A1_DB_PATH"] = str(ROOT / "data" / "test-maintenance.db")

from backend.app.main import app  # noqa: E402


client = TestClient(app)


def test_marketing_route_serves_incident_narrative_homepage() -> None:
    response = client.get("/marketing")

    assert response.status_code == 200
    html = response.text
    assert "Tri-MRO" in html
    assert "系统没有急着回答" in html
    assert "已阻断" in html
    assert "机械密封区域" in html
    assert "检修判断卡" in html
    assert "安全闸门" in html
    assert "知识写入流水线" in html
    assert "证据预算" in html
    assert "/static/marketing.css" in html
    assert "/static/marketing.js" in html


def test_promo_alias_uses_same_homepage() -> None:
    response = client.get("/promo")

    assert response.status_code == 200
    assert "基于三链对齐的可信设备检修作业控制平台" in response.text


def test_marketing_assets_are_accessible_and_contain_required_design_tokens() -> None:
    css = client.get("/static/marketing.css")
    js = client.get("/static/marketing.js")

    assert css.status_code == 200
    assert js.status_code == 200
    assert "--blocked" in css.text
    assert "--teal" in css.text
    assert ".incident-console" in css.text
    assert ".blocked-card" in css.text
    assert "marketingReady" in js.text
