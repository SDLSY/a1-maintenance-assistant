from __future__ import annotations

import hashlib
from typing import Any

from .component_contracts import infer_component_contract
from .evidence_budget import build_evidence_budget
from .fmea import build_fmea_risk_chain
from .safety_gate import attach_step_gates, build_safety_gate_state


SUPPORTED_EQUIPMENT = {"motor", "pump", "bearing", "engine"}


def _claim_id(equipment: str, model: str, text: str) -> str:
    digest = hashlib.sha1(f"{equipment}|{model}|{text}".encode("utf-8")).hexdigest()[:10]
    return f"claim_{equipment}_{digest}"


def _downgrade_evidence_budget(
    evidence_budget: dict[str, Any],
    *,
    max_score: float,
    decision: str,
    confidence_level: str,
    label: str,
    missing: str,
) -> dict[str, Any]:
    updated = dict(evidence_budget)
    updated["score"] = min(float(updated.get("score") or 0), max_score)
    updated["decision"] = decision
    updated["confidence_level"] = confidence_level
    updated["label"] = label
    missing_evidence = list(updated.get("missing_evidence") or [])
    if missing not in missing_evidence:
        missing_evidence.insert(0, missing)
    updated["missing_evidence"] = missing_evidence
    suggestions = list(updated.get("supplement_suggestions") or [])
    for item in ("补充设备铭牌或型号", "补充清晰现场图片", "提交人工复核意见"):
        if item not in suggestions:
            suggestions.append(item)
    updated["supplement_suggestions"] = suggestions[: max(1, len(missing_evidence))]
    return updated


def _detect_cross_modal_conflict(equipment: str, component_key: str, text: str, image_caption: str) -> bool:
    if not image_caption:
        return False
    caption = image_caption.lower()
    prompt = text.lower()
    conflict_rules = [
        (
            equipment == "pump",
            ["轴承外圈", "滚动体", "滚道", "outer ring", "rolling element", "spalling"],
            ["机械密封", "密封端", "shaft seal", "泄漏"],
        ),
        (
            equipment == "bearing",
            ["机械密封", "密封端", "泵体", "火花塞", "spark plug"],
            ["轴承", "外圈", "滚动体", "剥落"],
        ),
        (
            equipment == "engine" and component_key == "engine.spark_plug",
            ["机械密封", "泵体", "轴承外圈", "滚道"],
            ["火花塞", "spark plug", "点火"],
        ),
    ]
    for enabled, caption_terms, text_terms in conflict_rules:
        if enabled and any(term in caption for term in caption_terms) and any(term in prompt for term in text_terms):
            return True
    return False


def build_claim_card(
    *,
    text: str,
    equipment: str,
    model: str,
    visual_asset: dict[str, Any] | None,
    image_caption: str,
    citations: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    graph_paths: list[dict[str, Any]],
    sop: dict[str, Any],
    spatial_guidance: dict[str, Any],
    workflow_state: dict[str, Any],
    tri_mro_alignment: dict[str, Any],
) -> dict[str, Any]:
    component_keys = workflow_state.get("selected_component_keys", []) or []
    model_component_keys = workflow_state.get("selected_model_component_keys", []) or []
    contract = infer_component_contract(
        equipment,
        component_keys=component_keys,
        model_component_keys=model_component_keys,
        text=text,
    )
    if contract["component_key"] not in component_keys:
        component_keys = [contract["component_key"], *component_keys]
    evidence_budget = build_evidence_budget(
        citations=citations,
        cases=cases,
        graph_paths=graph_paths,
        visual_asset=visual_asset,
        image_caption=image_caption,
        model=model,
    )
    equipment_id = str(equipment or "").lower()
    unsupported_task = equipment_id not in SUPPORTED_EQUIPMENT or not str(text or "").strip()
    conflict_detected = _detect_cross_modal_conflict(
        equipment_id,
        contract["component_key"],
        text,
        image_caption,
    )
    if unsupported_task:
        evidence_budget = _downgrade_evidence_budget(
            evidence_budget,
            max_score=0.29,
            decision="refuse",
            confidence_level="insufficient",
            label="证据不足，不输出确定性判断",
            missing="受支持设备类型、设备型号或有效故障描述",
        )
    elif conflict_detected:
        evidence_budget = _downgrade_evidence_budget(
            evidence_budget,
            max_score=0.74,
            decision="confirm",
            confidence_level="medium",
            label="文本与视觉证据存在冲突，需要人工确认",
            missing="文本描述与图片证据一致性确认",
        )
    safety_gate = build_safety_gate_state(
        text=text,
        risk_level=sop.get("risk_level", "medium"),
        required_gates=contract.get("required_gates", []),
        sop_steps=sop.get("sop_steps", []),
        evidence_decision=evidence_budget["decision"],
    )
    operation_steps = attach_step_gates(
        tri_mro_alignment.get("operation_chain", []),
        safety_gate,
        sop.get("risk_level", "medium"),
    )
    fmea = build_fmea_risk_chain(
        contract["component_key"],
        sop.get("risk_level", "medium"),
        sop.get("possible_causes", []),
    )
    binding = contract.get("cad_binding", {})
    evidence_chain = {
        "items": tri_mro_alignment.get("evidence_chain", []),
        "manual_refs": [item for item in tri_mro_alignment.get("evidence_chain", []) if item.get("source_type") == "manual"],
        "case_refs": [item for item in tri_mro_alignment.get("evidence_chain", []) if item.get("source_type") == "case"],
        "graph_refs": [item for item in tri_mro_alignment.get("evidence_chain", []) if item.get("source_type") == "graph"],
        "visual_refs": [item for item in tri_mro_alignment.get("evidence_chain", []) if item.get("source_type") == "visual"],
    }
    review_needed = (
        evidence_budget["decision"] != "answer"
        or conflict_detected
        or unsupported_task
        or contract.get("manual_calibration_required", True)
        or safety_gate["state"] in {"BLOCKED", "NEED_REVIEW", "WAITING_SAFETY_CHECK"}
    )
    card = {
        "claim_id": _claim_id(equipment, model, text),
        "fault_claim": sop.get("diagnosis", text),
        "confidence_level": evidence_budget["confidence_level"],
        "evidence_budget": evidence_budget,
        "evidence_chain": evidence_chain,
        "structure_chain": {
            "equipment": equipment,
            "model": model,
            "component_keys": component_keys,
            "component_contract": contract,
            "cad_model_id": spatial_guidance.get("model_id", ""),
            "cad_anchor_type": binding.get("type", "semantic_hotspot"),
            "binding_precision_level": contract.get("binding_precision_level", "component"),
            "binding_precision_label": contract.get("binding_precision_label", "部件级绑定"),
            "binding_confidence": binding.get("confidence", tri_mro_alignment.get("structure_chain", {}).get("binding_confidence", 0)),
            "manual_calibration_required": contract.get("manual_calibration_required", True),
        },
        "operation_chain": {
            "steps": operation_steps,
            "sop_step_count": len(operation_steps),
            "blocked_step_count": sum(1 for item in operation_steps if item.get("decision") == "blocked"),
        },
        "fmea_risk_chain": fmea,
        "safety_gate": safety_gate,
        "review_policy": {
            "need_human_review": bool(review_needed),
            "reason": "文本与视觉证据冲突，需人工复核"
            if conflict_detected
            else "受支持设备类型、型号或故障描述不足，需补充资料"
            if unsupported_task
            else "证据不足、结构绑定需校准或安全闸门未放行"
            if review_needed
            else "证据、结构和安全状态满足受控作业要求",
            "conflict_detected": bool(conflict_detected),
            "unsupported_or_empty_task": bool(unsupported_task),
            "knowledge_write_allowed": evidence_budget["decision"] in {"answer", "confirm"} and safety_gate["state"] != "NEED_REVIEW",
        },
    }
    return card


def build_claim_cards(**kwargs: Any) -> list[dict[str, Any]]:
    return [build_claim_card(**kwargs)]
