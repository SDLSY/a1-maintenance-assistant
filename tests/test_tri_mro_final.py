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


def _pump_query(text: str = "离心泵机械密封持续滴漏，现场人员想直接拆泵端盖") -> dict:
    response = client.post(
        "/api/query",
        json={
            "text": text,
            "equipment": "pump",
            "model": "mini-vacuum-pump",
            "maintenance_level": "三级检修",
            "image_caption": "泵端机械密封区域有液体滴漏、油污和残液痕迹",
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_query_returns_claim_card_with_evidence_budget_fmea_and_safety_gate() -> None:
    body = _pump_query()

    assert body["claim_cards"]
    card = body["primary_claim_card"]
    assert card["claim_id"].startswith("claim_")
    assert card["fault_claim"] == body["diagnosis"]
    assert card["confidence_level"] in {"high", "medium", "low", "insufficient"}
    assert card["evidence_budget"]["score"] >= 0
    assert card["evidence_budget"]["decision"] in {"answer", "confirm", "direction_only", "refuse"}
    assert {"manual", "case", "graph", "visual"} <= set(card["evidence_budget"]["source_scores"])
    assert card["structure_chain"]["component_keys"]
    assert "pump.mechanical_seal" in card["structure_chain"]["component_keys"]
    assert card["operation_chain"]["steps"]
    assert card["fmea_risk_chain"]["failure_mode"]
    assert card["fmea_risk_chain"]["risk_priority"] > 0
    assert card["safety_gate"]["state"] in {
        "DRAFT",
        "WAITING_SAFETY_CHECK",
        "BLOCKED",
        "READY",
        "IN_PROGRESS",
        "NEED_REVIEW",
        "COMPLETED",
        "ARCHIVED",
    }
    assert card["review_policy"]["need_human_review"] is True
    assert body["tri_mro_alignment"]["claim_card_id"] == card["claim_id"]


def test_low_evidence_query_produces_refusal_or_direction_only_claim_card() -> None:
    body = client.post(
        "/api/query",
        json={
            "text": "未知型号设备有异味，图片模糊，没有铭牌和运行参数，能不能直接拆开",
            "equipment": "pump",
            "model": "UNKNOWN-XJ999",
            "maintenance_level": "一级检修",
            "top_k": 1,
        },
    ).json()
    card = body["primary_claim_card"]
    assert card["evidence_budget"]["decision"] in {"direction_only", "refuse", "confirm"}
    assert card["confidence_level"] in {"low", "insufficient", "medium"}
    assert card["evidence_budget"]["missing_evidence"]
    assert card["review_policy"]["need_human_review"] is True


def test_unsupported_equipment_or_empty_task_does_not_get_high_confidence_answer() -> None:
    for payload in (
        {
            "text": "这个设备好像坏了，图片也很模糊，没有铭牌，请直接告诉我怎么拆开维修。",
            "equipment": "unknown",
            "model": "",
            "maintenance_level": "一级检修",
            "top_k": 1,
        },
        {
            "text": "   ",
            "equipment": "",
            "model": "",
            "maintenance_level": "一级检修",
            "top_k": 1,
        },
    ):
        body = client.post("/api/query", json=payload).json()
        card = body["primary_claim_card"]
        assert card["evidence_budget"]["decision"] in {"direction_only", "refuse", "confirm"}
        assert card["confidence_level"] in {"low", "insufficient", "medium"}
        assert card["review_policy"]["need_human_review"] is True
        assert card["safety_gate"]["state"] in {"BLOCKED", "NEED_REVIEW", "WAITING_SAFETY_CHECK"}


def test_text_image_conflict_is_marked_for_human_review() -> None:
    body = client.post(
        "/api/query",
        json={
            "text": "离心泵机械密封持续泄漏，需要判断是否可以拆卸密封端盖。",
            "equipment": "pump",
            "model": "ISG80-160",
            "maintenance_level": "三级检修",
            "image_caption": "轴承外圈滚道有明显剥落、点蚀和滚动体压痕。",
            "top_k": 6,
        },
    ).json()
    card = body["primary_claim_card"]
    assert card["review_policy"]["need_human_review"] is True
    assert card["review_policy"]["conflict_detected"] is True
    assert card["evidence_budget"]["decision"] in {"confirm", "direction_only", "refuse"}


def test_3d_guidance_returns_component_contract_and_binding_precision() -> None:
    response = client.post(
        "/api/3d/guidance",
        json={
            "equipment": "pump",
            "model": "mini-vacuum-pump",
            "text": "机械密封泄漏，定位密封端并生成拆检导引",
            "sop_steps": ["断电挂牌并泄压", "拆检机械密封端盖"],
            "compliance": [],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["component_contract"]["component_key"] == "pump.mechanical_seal"
    assert body["component_contract"]["required_gates"]
    assert body["binding_precision_level"] in {"equipment", "component", "anchor", "geometry"}
    assert isinstance(body["manual_calibration_required"], bool)


def test_case_approval_returns_knowledge_write_pipeline_result() -> None:
    created = client.post(
        "/api/cases",
        json={
            "title": "Tri-MRO 测试：泵机械密封泄漏",
            "equipment": "pump",
            "model": "mini-vacuum-pump",
            "symptoms": "机械密封端持续滴漏",
            "fault_type": "pump.mechanical_seal",
            "cause": "密封端面磨损或密封圈老化",
            "actions": "断电泄压后拆检机械密封并复测泄漏",
            "parts": "机械密封,O形圈",
            "risk_level": "high",
        },
    ).json()
    approved = client.post(f"/api/cases/{created['id']}/approve")
    assert approved.status_code == 200
    body = approved.json()
    pipeline = body["knowledge_write"]
    assert pipeline["status"] == "approved"
    assert pipeline["kg_update"]["updated"] is True
    assert pipeline["index_update"]["updated"] is True
    assert "pump.mechanical_seal" in pipeline["affected_components"]
    assert pipeline["rollback_id"].startswith("rb_")
    assert pipeline["regression_test"]["safety_regression_passed"] is True


def test_metrics_expose_tri_mro_innovation_metrics() -> None:
    response = client.get("/api/metrics")
    assert response.status_code == 200
    metrics = response.json()["tri_mro_innovation_metrics"]
    expected = {
        "claim_traceability_rate",
        "tri_chain_coverage_rate",
        "cad_component_top1",
        "cad_component_top3",
        "high_risk_blocking_rate",
        "reasonable_refusal_rate",
        "knowledge_update_recall_gain",
        "knowledge_pollution_intercept_rate",
    }
    assert expected <= set(metrics)
    for key in expected:
        assert 0 <= metrics[key]["value"] <= 1


def test_frontend_exposes_tri_mro_final_objects() -> None:
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "primaryClaimCard" in app_js
    assert "innovationMetricsList" in app_js
    assert "latestKnowledgeWrite" in app_js
    assert "检修判断卡" in index_html
    assert "证据预算" in index_html
    assert "FMEA 风险链" in index_html
    assert "知识写入流水线" in index_html
    assert "创新指标" in index_html
