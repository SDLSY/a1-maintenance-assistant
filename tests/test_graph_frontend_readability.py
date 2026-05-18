from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_graph_frontend_uses_readable_focused_subgraph() -> None:
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "graphFocus" in app_js
    assert "readableGraph" in app_js
    assert "GRAPH_DISPLAY_LIMIT" in app_js
    assert "GRAPH_TYPE_LIMIT" in app_js
    assert "selected.length >= GRAPH_DISPLAY_LIMIT" in app_js
    assert "graph-control-rail" in index_html
    assert "graphEvidenceChains.length" in index_html
    assert "全量节点" in index_html


def test_graph_page_is_evidence_chain_workbench() -> None:
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert "graphEvidenceChains" in app_js
    assert "selectedGraphNode" in app_js
    assert "toggleGraphLayer" in app_js
    assert "graph-workbench" in index_html
    assert "evidence-chain" in index_html
    assert "graph-node-popover" in index_html
    assert "证据链路径步骤" in index_html
    assert ".evidence-chain" in css
    assert ".graph-node-popover" in css


def test_frontend_exposes_integrated_maintenance_session() -> None:
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert "currentSession" in app_js
    assert "workflowState" in app_js
    assert "updateCurrentSession" in app_js
    assert "prefillCaseFromCurrentSession" in app_js
    assert "returnToDiagnosisResult" in app_js
    assert "switchTab(child.id)" in index_html
    assert "toggleNavGroup(group.id)" in index_html
    assert "返回诊断结果" in index_html
    assert ".case-title-actions" in css
    assert "当前检修任务" in index_html
    assert "workflow-state-strip" in index_html
    assert "stage-timeline" in index_html
    assert "从当前任务生成案例" in index_html
    assert ".workflow-state-strip" in css
    assert ".stage-timeline" in css


def test_tri_mro_alignment_card_is_exposed_in_frontend() -> None:
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert "tri-mro-card" in index_html
    assert "证据链" in index_html
    assert "结构链" in index_html
    assert "作业链" in index_html
    assert "triMroAlignment" in app_js
    assert "triMroStatusLabel" in app_js
    assert ".tri-mro-card" in css


def test_candidate_cad_asset_pool_is_exposed_in_frontend() -> None:
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert "candidateCadAssets" in app_js
    assert "generateCandidateCadFromCurrentImage" in app_js
    assert "approveCandidateCad" in app_js
    assert "/api/cad/candidates/from-visual" in app_js
    assert "候选 CAD 资产池" in index_html
    assert "现场照片驱动" in index_html
    assert "非测量模型" in index_html
    assert ".candidate-cad-grid" in css
