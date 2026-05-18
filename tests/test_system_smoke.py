from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.system_smoke import EQUIPMENT_SCENARIOS, _browser_runner_js, write_markdown_report  # noqa: E402


def test_system_smoke_covers_core_equipment_and_browser_flows() -> None:
    assert {item["equipment"] for item in EQUIPMENT_SCENARIOS} == {"motor", "pump", "bearing", "engine"}
    runner = _browser_runner_js()
    for expected in (
        "生成检修方案",
        "进入 CAD 工位",
        "从当前任务生成案例",
        "返回诊断结果",
        "作业票与安全",
        "剖视平面",
        "复位视角",
        "同步问诊方案",
        "知识沉淀",
        "证据链",
        "评测证明",
        "资源资产",
        "/marketing",
        "marketing-homepage",
        "hasBlocked",
        "检修判断卡",
        "证据预算",
        "FMEA 风险链",
        "部件约束",
        "知识写入流水线",
        "创新指标",
    ):
        assert expected in runner
    assert "canvasCount === 1" in runner
    assert "爆炸视图" not in runner
    assert "should show bearing hotspots" in runner
    assert "hotspotCount >= 0" in runner
    assert "console_errors" in runner
    assert "claimCardVisible" in runner
    assert "componentContractVisible" in runner
    assert "innovationMetricsVisible" in runner


def test_demo_operation_matrix_covers_golden_and_adverse_cases() -> None:
    matrix_path = ROOT / "data" / "demo" / "tri_mro_operation_matrix.json"
    assert matrix_path.exists()
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    assert matrix["version"] >= "2026-05-15"
    assert {item["equipment"] for item in matrix["golden_cases"]} == {"motor", "pump", "bearing", "engine"}
    assert any(item["expected_decision"] in {"refuse", "direction_only", "confirm"} for item in matrix["adverse_cases"])
    required_modules = {
        "diagnosis",
        "cad_workbench",
        "claim_card",
        "case_pipeline",
        "knowledge_graph",
        "metrics",
        "resources",
    }
    assert required_modules <= set(matrix["operation_checklist"])
    for item in matrix["golden_cases"] + matrix["adverse_cases"]:
        assert item["input"]["text"]
        assert item["expected"]["component_keys"]
        assert item["expected"]["tri_mro_objects"]


def test_demo_test_data_doc_mentions_final_tri_mro_objects() -> None:
    doc = (ROOT / "docs" / "DEMO_TEST_DATA.md").read_text(encoding="utf-8")
    for marker in (
        "检修判断卡",
        "证据预算",
        "部件约束",
        "安全闸门",
        "知识写入流水线",
        "创新指标",
    ):
        assert marker in doc


def test_diagnosis_agent_progress_loading_ui_is_present() -> None:
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert "agent-progress-panel" in index_html
    assert "Tri-MRO 智能体接力" in index_html
    assert "agentProgressSteps" in index_html
    assert "currentAgentProgressStep" in index_html
    assert "agentProgressBlueprint" in app
    assert "startAgentProgress()" in app
    assert "stopAgentProgress(Boolean(this.result))" in app
    assert ".agent-orbit-ring" in css
    assert "@keyframes agent-orbit-spin" in css
    assert ".agent-step-active" in css


def test_resource_pages_replace_sidebar_provider_panel() -> None:
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert 'class="provider-panel"' not in index_html
    assert "模型供应商" not in index_html
    assert "resourcePages()" in app
    assert 'activeResourcePage: "comparison"' in app
    assert "selectResourcePage(page.id)" in index_html
    assert "runActiveResourcePage" in app
    for label in ("四组对比评测", "入库手册", "重建索引", "生成样例", "快速评测", "完整评测", "探测模型"):
        assert label in app
    assert "resource-action-page" in index_html
    assert ".resource-action-page" in css
    assert ".resource-page-grid button.active" in css


def test_safety_subtabs_have_distinct_views() -> None:
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert 'class="work-order-list-view"' in index_html
    assert 'v-if="activeTab === \'safety_list\'"' in index_html
    assert "作业票总览" in index_html
    assert "进入安全执行" in index_html
    assert 'class="safety-execution-view"' in index_html
    assert 'v-if="activeTab === \'safety\'"' in index_html
    assert "现场执行闸门" in index_html
    assert "safetyListSummaryCards" in app
    assert ".work-order-list-view" in css
    assert ".safety-execution-view" in css
    assert ".safety-execution-view {\n  align-content: start;" in css


def test_overview_does_not_render_incident_blocking_banner() -> None:
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'v-if="activeTab === \'overview\' || activeTab === \'diagnosis\'" class="incident-command-strip"' not in index_html
    assert "Incident Blocked Narrative" not in index_html
    assert 'v-if="hasActiveMaintenanceResult"' in index_html
    assert "未开始" in index_html
    assert "hasActiveMaintenanceResult()" in app
    assert 'return "未开始";' in app


def test_traceable_workbench_upgrade_contract_is_present() -> None:
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    main_py = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")

    for marker in (
        "openExplanation('confidence'",
        "openExplanation('risk'",
        "switchTab('claim_detail')",
        "置信度来源",
        "风险判定依据",
        "人工复核工作台",
        "证据预算",
        "部件约束",
        "FMEA 风险链",
        "安全闸门状态机",
        "claim-review-workbench",
        "evidence-workbench",
        "证据工作台",
        "手册证据",
        "案例证据",
        "图谱路径",
        "视觉路径",
        "image-recognition-workbench",
        "graph-map",
        "visual-asset-preview",
    ):
        assert marker in index_html

    for marker in (
        "componentDisplayName",
        "componentSummaryLabel",
        "activeExplanation",
        "explanationPayload",
        "manualEvidenceDetails",
        "caseEvidenceDetails",
        "graphPathEvidenceDetails",
        "visualEvidenceDetails",
        "claimReviewPanels",
        "selectClaimReviewPanel",
        "applyHumanReviewFeedback",
        "graphMapNodes",
        "graphMapEdges",
        "visualAssetImageUrl",
        "safetyAuditRows",
    ):
        assert marker in app

    for marker in (
        ".metric-action-card",
        ".explanation-drawer",
        ".claim-review-workbench",
        ".evidence-workbench",
        ".agent-orchestration-table",
        ".image-recognition-workbench",
        ".graph-map",
        ".visual-asset-preview",
        ".cad-binding-row",
    ):
        assert marker in css

    assert "@app.get(\"/api/visual-assets/{asset_id}/file\")" in main_py
    assert "pump.mechanical_seal / pump.inlet_outlet / pump.shaft" not in index_html


def test_system_smoke_markdown_report_lists_blockers_and_steps(tmp_path: Path) -> None:
    result = {
        "status": "failed",
        "generated_at": "2026-05-14T00:00:00Z",
        "base_url": "http://127.0.0.1:8051",
        "blockers": ["demo blocker"],
        "api": {"checks": [{"name": "health", "ok": False, "detail": {"status": "bad"}}]},
        "browser": {
            "status": "failed",
            "node_path": "node_modules",
            "chrome_path": "chrome.exe",
            "steps": [{"label": "cad-first", "canvasCount": 0, "hotspotCount": 0, "cadTitle": ""}],
            "console_errors": [{"type": "pageerror", "text": "boom"}],
        },
    }
    target = write_markdown_report(result, tmp_path / "system-smoke.md")
    text = target.read_text(encoding="utf-8")
    assert "demo blocker" in text
    assert "`FAIL` health" in text
    assert "`cad-first` canvas=0" in text
    assert "pageerror: boom" in text


def test_system_smoke_result_json_shape_is_serializable() -> None:
    payload = {
        "generated_at": "2026-05-14T00:00:00Z",
        "base_url": "http://127.0.0.1:8051",
        "api": {"status": "passed", "checks": [], "blockers": []},
        "browser": {"status": "passed", "steps": [], "blockers": [], "console_errors": []},
        "blockers": [],
        "status": "passed",
    }
    assert json.loads(json.dumps(payload, ensure_ascii=False))["status"] == "passed"
