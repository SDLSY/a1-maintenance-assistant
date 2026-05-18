from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "data" / "demo" / "tri_mro_test_cases.json"
DEFAULT_OUTPUT_DIR = ROOT / "test-results"


def _configure_local_runtime() -> None:
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("ACTIVE_MODEL_PROVIDER", "local")
    os.environ.setdefault("TEXT_AGENT_PROVIDER", "local")
    os.environ.setdefault("VISION_AGENT_PROVIDER", "local")
    os.environ.setdefault("EMBEDDING_AGENT_PROVIDER", "local")
    os.environ.setdefault("COMPLIANCE_AGENT_PROVIDER", "local")
    os.environ.setdefault("KNOWLEDGE_AGENT_PROVIDER", "local")
    os.environ.setdefault("A1_DB_PATH", str(ROOT / "data" / "test-maintenance.db"))


def _client() -> TestClient:
    _configure_local_runtime()
    from backend.app.database import reset_demo_db
    from backend.app.main import app

    reset_demo_db()
    return TestClient(app)


def _load_cases() -> dict[str, Any]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _ok(detail: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": "passed", "detail": detail, "evidence": evidence or {}}


def _fail(detail: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": "failed", "detail": detail, "evidence": evidence or {}}


class RunnerContext:
    def __init__(self, client: TestClient, fixture: dict[str, Any]) -> None:
        self.client = client
        self.fixture = fixture
        self.query_cache: dict[str, dict[str, Any]] = {}
        self.created_cases: dict[str, int] = {}

    def golden(self, case_id: str) -> dict[str, Any]:
        return next(item for item in self.fixture["golden_cases"] if item["id"] == case_id)

    def query(self, case_id: str) -> dict[str, Any]:
        if case_id in self.query_cache:
            return self.query_cache[case_id]
        item = self.golden(case_id)
        response = self.client.post(
            "/api/query",
            json={
                "equipment": item["equipment"],
                "model": item["model"],
                "maintenance_level": "三级检修" if item["equipment"] == "pump" else "二级检修",
                "text": item["text"],
                "image_caption": item.get("image_caption", ""),
                "top_k": 6,
            },
        )
        if response.status_code != 200:
            raise AssertionError(f"{case_id} query status={response.status_code}")
        self.query_cache[case_id] = response.json()
        return self.query_cache[case_id]


def _assert_claim_card(card: dict[str, Any]) -> None:
    required = {
        "claim_id",
        "fault_claim",
        "confidence_level",
        "evidence_budget",
        "evidence_chain",
        "structure_chain",
        "operation_chain",
        "fmea_risk_chain",
        "safety_gate",
        "review_policy",
    }
    missing = required - set(card)
    if missing:
        raise AssertionError(f"Claim Card missing {sorted(missing)}")


def _evidence_decision_ok(budget: dict[str, Any]) -> bool:
    score = float(budget.get("score") or 0)
    decision = budget.get("decision")
    if score >= 0.75:
        return decision == "answer"
    if score >= 0.50:
        return decision in {"confirm", "direction_only", "refuse"}
    if score >= 0.30:
        return decision in {"direction_only", "refuse"}
    return decision == "refuse"


def _create_case(ctx: RunnerContext) -> int:
    if "pump" in ctx.created_cases:
        return ctx.created_cases["pump"]
    response = ctx.client.post(
        "/api/cases",
        json={
            "title": "Tri-MRO 全测试：离心泵机械密封泄漏",
            "equipment": "pump",
            "model": "ISG80-160",
            "symptoms": "机械密封持续滴漏，密封端有泄漏痕迹。",
            "fault_type": "pump.mechanical_seal",
            "cause": "密封端面磨损或 O 形圈老化",
            "actions": "断电挂牌、隔离介质、泄压后拆检机械密封并复测。",
            "parts": "机械密封组件,O形圈,轴套",
            "risk_level": "high",
        },
    )
    if response.status_code != 200:
        raise AssertionError(f"create case status={response.status_code}")
    case_id = int(response.json()["id"])
    ctx.created_cases["pump"] = case_id
    return case_id


def _run_health(ctx: RunnerContext) -> dict[str, Any]:
    response = ctx.client.get("/api/health")
    return _ok("health ok", response.json()) if response.status_code == 200 and response.json().get("status") == "ok" else _fail("health failed")


def _run_frontend_static(_: RunnerContext) -> dict[str, Any]:
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    corpus = f"{index}\n{app_js}"
    required = ["检修任务台", "CAD 结构工位", "证据链图谱", "案例沉淀", "评测证明", "资源与模型"]
    missing = [item for item in required if item not in corpus]
    return _ok("frontend navigation labels present") if not missing else _fail("frontend labels missing", {"missing": missing})


def _run_motor_text(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.query("G01")
    keys = body["primary_claim_card"]["structure_chain"]["component_keys"]
    ok = "motor.bearing" in keys and body["citations"] and body["sop_steps"]
    return _ok("motor bearing text query passed", {"component_keys": keys}) if ok else _fail("motor query failed", {"component_keys": keys})


def _run_upload_image(ctx: RunnerContext) -> dict[str, Any]:
    image_dir = ROOT / "data" / "image_eval" / "images"
    image = image_dir / "pump_mechanical_seal_parts_02.jpg"
    if not image.exists():
        image = next(image_dir.glob("*.jpg"))
    with image.open("rb") as handle:
        response = ctx.client.post("/api/upload-image", files={"file": (image.name, handle, "image/jpeg")})
    if response.status_code != 200:
        return _fail("upload failed", {"status_code": response.status_code})
    body = response.json()
    analysis = body.get("visual_analysis") or {}
    ok = bool(body.get("visual_asset_id")) and bool(analysis.get("component_candidates"))
    return _ok("image upload generated visual asset", {"image": str(image), "asset_id": body.get("visual_asset_id")}) if ok else _fail("visual analysis incomplete", body)


def _run_pump_filter(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.query("G02")
    keys = body["primary_claim_card"]["structure_chain"]["component_keys"]
    ok = any(key.startswith("pump.") for key in keys) and body["citations"]
    return _ok("pump query stayed in pump component space", {"component_keys": keys}) if ok else _fail("pump filter failed", {"component_keys": keys})


def _run_multimodal(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.query("G02")
    budget = body["primary_claim_card"]["evidence_budget"]
    visual_refs = body["primary_claim_card"]["evidence_chain"].get("visual_refs", [])
    ok = budget["source_scores"]["visual"] > 0 and bool(visual_refs)
    return _ok("visual evidence participated", {"visual_score": budget["source_scores"]["visual"]}) if ok else _fail("visual evidence missing", budget)


def _run_retrieval(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.query("G02")
    ok = bool(body["citations"]) and bool(body["similar_cases"]) and bool(body["graph_paths"])
    return _ok("manual/case/graph retrieval passed", {"citations": len(body["citations"]), "cases": len(body["similar_cases"]), "graph": len(body["graph_paths"])}) if ok else _fail("retrieval incomplete")


def _run_manual_refs(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.query("G02")
    citations = body["citations"]
    ok = any(item.get("title") and (item.get("summary") or item.get("content")) for item in citations)
    return _ok("manual references traceable", {"citations": len(citations)}) if ok else _fail("manual refs not traceable")


def _run_sop_all_golden(ctx: RunnerContext) -> dict[str, Any]:
    failed: list[str] = []
    counts: dict[str, int] = {}
    for case_id in ("G01", "G02", "G03", "G04"):
        body = ctx.query(case_id)
        counts[case_id] = len(body.get("sop_steps") or [])
        if counts[case_id] < 6 or not body.get("compliance") or not body.get("acceptance"):
            failed.append(case_id)
    return _ok("all golden SOP outputs are complete", counts) if not failed else _fail("SOP incomplete", {"failed": failed, "counts": counts})


def _run_sop_distinct(ctx: RunnerContext) -> dict[str, Any]:
    joined = {case_id: " ".join(ctx.query(case_id).get("sop_steps") or []) for case_id in ("G01", "G02", "G03", "G04")}
    unique_count = len(set(joined.values()))
    return _ok("equipment-specific SOPs differ", {"unique": unique_count}) if unique_count == 4 else _fail("SOPs are not equipment-specific", {"unique": unique_count})


def _run_maintenance_level(ctx: RunnerContext) -> dict[str, Any]:
    low = ctx.client.post("/api/query", json={"equipment": "pump", "model": "ISG80-160", "maintenance_level": "一级检修", "text": "离心泵机械密封泄漏。", "top_k": 6}).json()
    high = ctx.client.post("/api/query", json={"equipment": "pump", "model": "ISG80-160", "maintenance_level": "三级检修", "text": "离心泵机械密封泄漏，需要拆检。", "top_k": 6}).json()
    ok = len(high.get("sop_steps") or []) >= len(low.get("sop_steps") or [])
    return _ok("maintenance level does not reduce SOP completeness", {"low": len(low.get("sop_steps") or []), "high": len(high.get("sop_steps") or [])}) if ok else _fail("high level SOP shorter than low level")


def _run_tools_acceptance(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.query("G02")
    ok = bool(body.get("tools_and_parts")) and bool(body.get("acceptance"))
    return _ok("tools and acceptance present", {"tools": body.get("tools_and_parts"), "acceptance": body.get("acceptance")}) if ok else _fail("tools or acceptance missing")


def _run_safety_block(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.post("/api/query", json={"equipment": "pump", "model": "ISG80-160", "maintenance_level": "三级检修", "text": "这台泵密封漏了，我想直接拆开看看。", "top_k": 6}).json()
    gate = body["primary_claim_card"]["safety_gate"]
    return _ok("direct disassembly blocked", gate) if gate["state"] == "BLOCKED" else _fail("direct disassembly not blocked", gate)


def _run_required_gate(ctx: RunnerContext, gate: str) -> dict[str, Any]:
    body = ctx.query("G02")
    gates = body["primary_claim_card"]["safety_gate"].get("required_gates", [])
    return _ok(f"{gate} required", {"gates": gates}) if gate in gates else _fail(f"{gate} missing", {"gates": gates})


def _run_audit_log(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.query("G02")
    log = body["primary_claim_card"]["safety_gate"].get("audit_log", [])
    ok = bool(log) and {"time", "actor", "event"} <= set(log[0])
    return _ok("safety audit log present", {"audit_log": log[:1]}) if ok else _fail("audit log missing", {"audit_log": log})


def _run_fail_closed(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.post("/api/query", json={"equipment": "unknown", "model": "", "maintenance_level": "一级检修", "text": "这个设备好像坏了，图片模糊，没有铭牌，请直接拆开维修。", "top_k": 1}).json()
    card = body["primary_claim_card"]
    ok = card["evidence_budget"]["decision"] != "answer" and card["safety_gate"]["state"] in {"BLOCKED", "NEED_REVIEW", "WAITING_SAFETY_CHECK"}
    return _ok("unsupported or weak evidence fails closed", card["evidence_budget"]) if ok else _fail("weak evidence did not fail closed", card)


def _run_case_pending(ctx: RunnerContext) -> dict[str, Any]:
    case_id = _create_case(ctx)
    pending = ctx.client.get("/api/cases?status=pending").json()["cases"]
    approved = ctx.client.get("/api/cases?status=approved").json()["cases"]
    ok = any(item["id"] == case_id for item in pending) and not any(item["id"] == case_id for item in approved)
    return _ok("pending case is not in approved list", {"case_id": case_id}) if ok else _fail("pending case polluted approved list", {"case_id": case_id})


def _run_case_approve(ctx: RunnerContext) -> dict[str, Any]:
    case_id = _create_case(ctx)
    response = ctx.client.post(f"/api/cases/{case_id}/approve")
    body = response.json()
    kw = body.get("knowledge_write") or {}
    ok = response.status_code == 200 and body.get("status") == "approved" and kw.get("kg_update", {}).get("updated") and kw.get("index_update", {}).get("updated")
    return _ok("case approved and knowledge write recorded", {"case_id": case_id, "knowledge_write": kw}) if ok else _fail("case approval failed", body)


def _run_models(ctx: RunnerContext) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for equipment in ("motor", "pump", "bearing", "engine"):
        body = ctx.client.get(f"/api/3d/models?equipment={equipment}").json()
        models = body.get("models") or []
        details[equipment] = [item.get("id") for item in models[:3]]
        if not models or any(item.get("equipment") != equipment for item in models[:3]):
            return _fail("3D models invalid", details)
    return _ok("3D models available for four equipment types", details)


def _run_guidance(ctx: RunnerContext) -> dict[str, Any]:
    from backend.app.component_taxonomy import canonical_component_key

    failed: list[str] = []
    detail: dict[str, Any] = {}
    for case_id in ("G01", "G02", "G03", "G04"):
        item = ctx.golden(case_id)
        body = ctx.client.post("/api/3d/guidance", json={"equipment": item["equipment"], "model": item["model"], "text": item["text"], "sop_steps": ctx.query(case_id).get("sop_steps", []), "compliance": []}).json()
        keys = [
            canonical_component_key(item["equipment"], component.get("component_key"))
            for component in body.get("highlighted_components", [])
        ]
        detail[case_id] = keys
        expected = item["expected_component_keys"]
        if not any(key in keys for key in expected):
            failed.append(case_id)
    return _ok("3D guidance highlights expected components", detail) if not failed else _fail("3D guidance component mismatch", {"failed": failed, "detail": detail})


def _run_cad_bridge(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.get("/api/3d/models/freecad_6201_2rs_bearing").json()
    bridge = body.get("cad_bridge") or {}
    ok = bool(bridge.get("cad_source", {}).get("exists")) and bool(bridge.get("glb_viewer", {}).get("exists")) and bool(bridge.get("trace_chain"))
    return _ok("CAD bridge exposes source and binding quality", {"model_id": body.get("id")}) if ok else _fail("CAD bridge incomplete", body)


def _run_claim_fields(ctx: RunnerContext) -> dict[str, Any]:
    failed: list[str] = []
    for case_id in ("G01", "G02", "G03", "G04"):
        try:
            _assert_claim_card(ctx.query(case_id)["primary_claim_card"])
        except AssertionError:
            failed.append(case_id)
    return _ok("Claim Card fields complete for golden cases") if not failed else _fail("Claim Card incomplete", {"failed": failed})


def _run_confidence_consistency(ctx: RunnerContext) -> dict[str, Any]:
    failed = []
    for case_id in ("G01", "G02", "G03", "G04"):
        budget = ctx.query(case_id)["primary_claim_card"]["evidence_budget"]
        if not _evidence_decision_ok(budget):
            failed.append({"case": case_id, "budget": budget})
    return _ok("Evidence Budget decisions match score thresholds") if not failed else _fail("Evidence Budget inconsistency", {"failed": failed})


def _run_operation_chain(ctx: RunnerContext) -> dict[str, Any]:
    card = ctx.query("G02")["primary_claim_card"]
    steps = card["operation_chain"]["steps"]
    ok = bool(steps) and all(item.get("component_key") for item in steps[:3])
    return _ok("operation chain binds SOP steps to components", {"steps": len(steps)}) if ok else _fail("operation chain missing component binding")


def _run_review_policy(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.post("/api/query", json={"equipment": "pump", "model": "ISG80-160", "text": "离心泵机械密封持续泄漏，需要判断是否可以拆卸密封端盖。", "image_caption": "轴承外圈滚道有明显剥落、点蚀和滚动体压痕。", "top_k": 6}).json()
    policy = body["primary_claim_card"]["review_policy"]
    return _ok("conflict triggers human review", policy) if policy.get("need_human_review") and policy.get("conflict_detected") else _fail("conflict did not trigger review", policy)


def _run_evidence_scores(ctx: RunnerContext) -> dict[str, Any]:
    budget = ctx.query("G02")["primary_claim_card"]["evidence_budget"]
    ok = {"manual", "case", "graph", "visual"} <= set(budget.get("source_scores", {}))
    return _ok("four evidence source scores present", budget) if ok else _fail("source scores incomplete", budget)


def _run_low_evidence(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.post("/api/query", json={"equipment": "unknown", "model": "", "text": "未知设备发生异常，请直接给维修结论。", "top_k": 1}).json()
    card = body["primary_claim_card"]
    ok = card["evidence_budget"]["decision"] != "answer" and card["review_policy"]["need_human_review"]
    return _ok("unsupported equipment downgraded", card["evidence_budget"]) if ok else _fail("unsupported equipment got answer", card)


def _run_conflict(ctx: RunnerContext) -> dict[str, Any]:
    return _run_review_policy(ctx)


def _run_fmea(ctx: RunnerContext) -> dict[str, Any]:
    fmea = ctx.query("G02")["primary_claim_card"]["fmea_risk_chain"]
    required = {"failure_mode", "possible_causes", "effects", "severity", "occurrence", "detectability", "risk_priority", "recommended_action"}
    ok = required <= set(fmea) and fmea.get("risk_priority", 0) > 0
    return _ok("FMEA risk chain complete", fmea) if ok else _fail("FMEA incomplete", fmea)


def _run_component_consistency(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.query("G02")
    workflow_keys = set(body["workflow_state"]["selected_component_keys"])
    claim_keys = set(body["primary_claim_card"]["structure_chain"]["component_keys"])
    spatial_keys = {item.get("component_key") for item in body["spatial_guidance"].get("highlighted_components", [])}
    ok = "pump.mechanical_seal" in claim_keys and bool(workflow_keys & claim_keys) and bool(spatial_keys)
    return _ok("component keys stay in same equipment namespace", {"workflow": list(workflow_keys), "claim": list(claim_keys), "spatial": list(spatial_keys)}) if ok else _fail("component key drift", {"workflow": list(workflow_keys), "claim": list(claim_keys), "spatial": list(spatial_keys)})


def _run_alias(_: RunnerContext) -> dict[str, Any]:
    from backend.app.component_contracts import infer_component_contract

    contract = infer_component_contract("pump", text="shaft seal leakage near pump shaft")
    return _ok("shaft seal alias mapped", contract) if contract["component_key"] == "pump.mechanical_seal" else _fail("alias mapping failed", contract)


def _run_binding_level(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.post("/api/3d/guidance", json={"equipment": "pump", "model": "ISG80-160", "text": "机械密封泄漏"}).json()
    ok = body.get("binding_precision_level") in {"equipment", "component", "anchor", "geometry"} and "manual_calibration_required" in body
    return _ok("binding level visible", {"level": body.get("binding_precision_level"), "manual": body.get("manual_calibration_required")}) if ok else _fail("binding level missing", body)


def _run_metrics(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.get("/api/metrics").json()
    metrics = body.get("tri_mro_innovation_metrics") or {}
    ok = bool(metrics) and "tri_chain_coverage_rate" in metrics
    return _ok("innovation metrics present", {"keys": sorted(metrics)}) if ok else _fail("innovation metrics missing", body)


def _run_comparison(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.post("/api/eval/run-comparison?max_questions=3").json()
    comparison = body.get("comparison") or body
    text = json.dumps(comparison, ensure_ascii=False)
    ok = all(item in text for item in ("no_rag", "text_rag", "multimodal_rag", "full_system"))
    return _ok("four-way comparison runnable", {"keys": sorted(comparison)[:8]}) if ok else _fail("comparison missing modes", body)


def _run_resources(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.get("/api/resources/verification").json()
    critical = (body.get("summary") or {}).get("critical_failures") or []
    return _ok("resources have no critical failures", {"critical_failures": critical}) if not critical else _fail("critical resource failures", {"critical_failures": critical})


def _run_image_status(ctx: RunnerContext) -> dict[str, Any]:
    response = ctx.client.get("/api/image-eval/status")
    return _ok("image eval status readable", response.json()) if response.status_code == 200 else _fail("image eval status failed", {"status_code": response.status_code})


def _run_graph(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.client.get("/api/knowledge-graph").json()
    ok = bool(body.get("nodes")) and bool(body.get("edges"))
    return _ok("knowledge graph non-empty", {"nodes": len(body.get("nodes") or []), "edges": len(body.get("edges") or [])}) if ok else _fail("knowledge graph empty", body)


def _run_fallback(ctx: RunnerContext) -> dict[str, Any]:
    body = ctx.query("G01")
    review = body.get("model_review") or {}
    ok = bool(review.get("text")) and review.get("provider") in {"local", "openai", "opencode", "codex", "spatialai"}
    return _ok("model route returned review/fallback text", review) if ok else _fail("fallback route missing", review)


def _run_empty_input(ctx: RunnerContext) -> dict[str, Any]:
    response = ctx.client.post("/api/query", json={"equipment": "", "model": "", "text": "", "top_k": 1})
    if response.status_code == 422:
        return _ok("empty input rejected by schema", {"status_code": 422})
    body = response.json()
    decision = body["primary_claim_card"]["evidence_budget"]["decision"]
    return _ok("empty input did not produce answer", {"decision": decision}) if decision != "answer" else _fail("empty input produced high-confidence answer", body)


def _run_review_log(ctx: RunnerContext) -> dict[str, Any]:
    result = _run_case_approve(ctx)
    if result["status"] != "passed":
        return result
    kw = result["evidence"]["knowledge_write"]
    ok = bool(kw.get("audit_log")) and bool(kw.get("rollback_id")) and bool(kw.get("affected_components"))
    return _ok("review audit log exists", {"rollback_id": kw.get("rollback_id"), "affected_components": kw.get("affected_components")}) if ok else _fail("review audit log incomplete", kw)


HANDLERS: dict[str, Callable[[RunnerContext], dict[str, Any]]] = {
    "T01": _run_health,
    "T02": _run_frontend_static,
    "T03": _run_motor_text,
    "T04": _run_upload_image,
    "T05": _run_pump_filter,
    "T06": _run_multimodal,
    "T07": _run_multimodal,
    "T08": _run_retrieval,
    "T09": _run_retrieval,
    "T10": _run_manual_refs,
    "T20": _run_sop_all_golden,
    "T21": _run_sop_distinct,
    "T22": _run_maintenance_level,
    "T23": _run_tools_acceptance,
    "T24": _run_tools_acceptance,
    "T25": _run_safety_block,
    "T26": _run_safety_block,
    "T27": lambda ctx: _run_required_gate(ctx, "pressure_released"),
    "T28": lambda ctx: _run_required_gate(ctx, "ppe_confirmed"),
    "T29": _run_audit_log,
    "T30": _run_safety_block,
    "T31": _run_fail_closed,
    "T40": _run_case_pending,
    "T41": _run_case_pending,
    "T42": _run_case_approve,
    "T44": _run_case_approve,
    "T50": _run_models,
    "T51": _run_guidance,
    "T54": _run_cad_bridge,
    "T60": _run_claim_fields,
    "T61": _run_component_consistency,
    "T62": _run_confidence_consistency,
    "T64": _run_component_consistency,
    "T65": _run_operation_chain,
    "T66": _run_review_policy,
    "T68": _run_evidence_scores,
    "T69": _run_low_evidence,
    "T70": _run_low_evidence,
    "T71": _run_conflict,
    "T73": _run_fmea,
    "T74": _run_fmea,
    "T75": lambda ctx: _run_required_gate(ctx, "pressure_released"),
    "T76": _run_component_consistency,
    "T77": _run_alias,
    "T78": _run_binding_level,
    "T80": _run_metrics,
    "T81": _run_comparison,
    "T82": _run_resources,
    "T83": _run_image_status,
    "T90": _run_graph,
    "T92": _run_retrieval,
    "T110": _run_fallback,
    "T111": _run_empty_input,
    "T121": _run_review_log,
}


def _status_for_non_automated(case: dict[str, Any]) -> dict[str, Any]:
    mode = case["execution_mode"]
    if mode == "browser_smoke":
        return {"status": "browser_smoke_required", "detail": "由 scripts/system_smoke.py 执行", "evidence": {}}
    if mode == "environment":
        return {"status": "environment_blocked", "detail": "需要 LoongArch + 银河麒麟或对应目标环境", "evidence": {}}
    if mode == "not_implemented":
        return {"status": "not_implemented", "detail": "当前系统没有完整实现该测试所需接口或权限模型", "evidence": {}}
    return {"status": "manual_required", "detail": "需要人工机械判断、UI 操作或真实图片主观验收", "evidence": {}}


def execute_plan(output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    fixture = _load_cases()
    ctx = RunnerContext(_client(), fixture)
    rows: list[dict[str, Any]] = []

    for case in fixture["test_cases"]:
        result: dict[str, Any]
        if case["execution_mode"] in {"manual", "environment", "not_implemented", "browser_smoke"} and case["id"] not in HANDLERS:
            result = _status_for_non_automated(case)
        else:
            handler = HANDLERS.get(case["id"])
            if not handler:
                result = _fail("automated handler missing")
            else:
                try:
                    result = handler(ctx)
                except Exception as exc:  # noqa: BLE001
                    result = _fail(f"{type(exc).__name__}: {exc}")
        rows.append({**case, **result})

    summary = {
        "total": len(rows),
        "passed": sum(1 for item in rows if item["status"] == "passed"),
        "automated_passed": sum(1 for item in rows if item["status"] == "passed" and item["execution_mode"] == "automated"),
        "failed": sum(1 for item in rows if item["status"] == "failed"),
        "browser_smoke_required": sum(1 for item in rows if item["status"] == "browser_smoke_required"),
        "manual_required": sum(1 for item in rows if item["status"] == "manual_required"),
        "environment_blocked": sum(1 for item in rows if item["status"] == "environment_blocked"),
        "not_implemented": sum(1 for item in rows if item["status"] == "not_implemented"),
    }
    summary["manual_or_environment"] = (
        summary["browser_smoke_required"]
        + summary["manual_required"]
        + summary["environment_blocked"]
        + summary["not_implemented"]
    )
    result = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "case_source": str(CASES_PATH),
        "summary": summary,
        "results": rows,
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "tri-mro-full-test-execution.json"
    md_path = out_dir / "tri-mro-full-test-execution.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(result, md_path)
    return result


def _write_markdown(result: dict[str, Any], target: Path) -> None:
    lines = [
        "# Tri-MRO 完整测试执行报告",
        "",
        f"- Generated at: `{result['generated_at']}`",
        f"- Case source: `{result['case_source']}`",
        "",
        "## Summary",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Results", "", "| ID | Priority | Module | Mode | Status | Detail |", "|---|---|---|---|---|---|"])
    for item in result["results"]:
        detail = str(item.get("detail", "")).replace("|", "/")
        lines.append(
            f"| {item['id']} | {item['priority']} | {item['module']} | {item['execution_mode']} | {item['status']} | {detail} |"
        )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    result = execute_plan()
    print(json.dumps({"status": "passed" if result["summary"]["failed"] == 0 else "failed", "summary": result["summary"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
