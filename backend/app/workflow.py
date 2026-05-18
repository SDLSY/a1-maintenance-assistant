from __future__ import annotations

import hashlib
from typing import Any

from .component_taxonomy import canonical_component_key, canonicalize_highlighted_components, component_confidence_status


def _task_id(*parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    return "a1-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _stage(id_: str, label: str, status: str, summary: str, evidence_refs: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": id_,
        "label": label,
        "status": status,
        "summary": summary,
        "evidence_refs": evidence_refs or [],
    }


def _safety_status(spatial_guidance: dict[str, Any]) -> dict[str, Any]:
    gate = spatial_guidance.get("safety_gate", {}) or {}
    status = gate.get("status", "needs_confirmation")
    blocking = list(gate.get("blocking_reasons", []) or [])
    return {
        "status": status,
        "label": gate.get("label", "等待安全确认"),
        "blocking_items": blocking,
        "failed_count": gate.get("failed_count", len(blocking)),
        "decision": gate.get("decision", ""),
    }


def build_workflow_state(
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
    resource_summary: dict[str, Any],
) -> dict[str, Any]:
    highlighted = spatial_guidance.get("highlighted_components", []) or []
    canonical_components = canonicalize_highlighted_components(equipment, highlighted)
    selected_component_keys = []
    for item in canonical_components:
        key = item["canonical_component_key"]
        if key not in selected_component_keys:
            selected_component_keys.append(key)
    selected_model_component_keys = [
        str(item.get("component_key"))
        for item in highlighted
        if item.get("component_key")
    ]
    max_confidence = max([float(item.get("confidence") or 0) for item in highlighted] or [0])
    cad_status = component_confidence_status(max_confidence)
    safety_gate = _safety_status(spatial_guidance)
    verified = int((resource_summary.get("summary") or {}).get("verified") or 0)
    total_resources = int((resource_summary.get("summary") or {}).get("total") or 0)
    has_visual = bool(visual_asset or image_caption)

    stages = [
        _stage(
            "vision",
            "OCR+VLM 现场感知",
            "done" if has_visual else "skipped",
            "已接入图片结构化结果" if visual_asset else "本次使用文本与型号检索" if not image_caption else "使用图片描述参与检索",
            [f"visual_asset:{visual_asset['id']}"] if visual_asset else (["image_caption"] if image_caption else []),
        ),
        _stage(
            "retrieval",
            "手册/案例/图谱检索",
            "done" if citations or cases else "needs_review",
            f"命中 {len(citations)} 条手册证据、{len(cases)} 条案例证据、{len(graph_paths)} 条图谱路径",
            [item.get("title", "") for item in citations[:3] if item.get("title")],
        ),
        _stage(
            "cad_grounding",
            "CAD 部件定位",
            cad_status,
            f"标准模型 {spatial_guidance.get('model_id', '未选择')} 定位到 {', '.join(selected_component_keys) or '待复核部件'}",
            [spatial_guidance.get("model_id", ""), *selected_model_component_keys],
        ),
        _stage(
            "sop",
            "SOP 作业指导",
            "done" if sop.get("sop_steps") else "needs_review",
            f"生成 {len(sop.get('sop_steps', []))} 个步骤，绑定 {len(spatial_guidance.get('sop_bindings', []) or [])} 个 3D 步骤",
            [str(item.get("step_index")) for item in (spatial_guidance.get("sop_bindings", []) or [])[:5]],
        ),
        _stage(
            "safety_gate",
            "安全闸门",
            "done" if safety_gate["status"] == "ready" else safety_gate["status"],
            safety_gate["decision"] or safety_gate["label"],
            safety_gate["blocking_items"],
        ),
        _stage(
            "case_loop",
            "案例沉淀",
            "ready",
            "当前任务可生成待审核工单，审核后进入案例库与知识图谱",
            selected_component_keys,
        ),
        _stage(
            "evaluation",
            "评测证明",
            "done" if verified else "needs_review",
            f"资源验证 {verified}/{total_resources}，评测页用于展示完整链路指标",
            ["resource_verification"],
        ),
    ]

    return {
        "task_id": _task_id(equipment, model, text, visual_asset.get("id") if visual_asset else "", image_caption),
        "equipment": equipment,
        "model": model,
        "selected_component_keys": selected_component_keys,
        "selected_model_component_keys": selected_model_component_keys,
        "component_groundings": canonical_components,
        "safety_gate": safety_gate,
        "stages": stages,
        "next_actions": [
            "在 CAD 结构工位复核高亮部件",
            "按 SOP 完成安全闸门确认",
            "从当前任务生成案例并提交审核",
        ],
    }


def _evidence_item(index: int, source_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    title = payload.get("title") or payload.get("summary") or payload.get("section") or source_type
    return {
        "evidence_id": f"{source_type}:{index}",
        "source_type": source_type,
        "title": title,
        "summary": payload.get("content") or payload.get("summary") or payload.get("section") or title,
        "page": payload.get("page"),
        "source": payload.get("source", ""),
        "source_url": payload.get("source_url", ""),
        "license": payload.get("license", ""),
        "modality": payload.get("modality", source_type),
        "confidence": round(float(payload.get("confidence") or 0), 2),
        "verified": bool(payload.get("source_url") or payload.get("source") or source_type in {"graph", "visual"}),
    }


def _visual_evidence(visual_asset: dict[str, Any] | None, image_caption: str) -> list[dict[str, Any]]:
    if not visual_asset and not image_caption:
        return []
    analysis = (visual_asset or {}).get("analysis") or {}
    labels = [
        item.get("label", "")
        for item in analysis.get("defect_labels", [])
        if isinstance(item, dict) and item.get("label")
    ]
    return [
        {
            "evidence_id": f"visual:{(visual_asset or {}).get('id', 'caption')}",
            "source_type": "visual",
            "title": (visual_asset or {}).get("filename", "图片结构化描述"),
            "summary": analysis.get("caption") or image_caption or "图片输入已参与跨模态检索。",
            "page": None,
            "source": (visual_asset or {}).get("stored_path", ""),
            "source_url": "",
            "license": "local_uploaded_or_verified_visual_asset",
            "modality": "image",
            "confidence": 0.86 if visual_asset else 0.62,
            "verified": bool(visual_asset),
            "visual_labels": labels,
            "ocr_text": analysis.get("ocr_text", ""),
        }
    ]


def _graph_evidence(graph_paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence = []
    for index, path in enumerate(graph_paths[:5], start=1):
        nodes = path.get("nodes") or path.get("path") or []
        if isinstance(nodes, list):
            summary = " -> ".join(str(item.get("label", item)) if isinstance(item, dict) else str(item) for item in nodes[:6])
        else:
            summary = str(nodes)
        evidence.append(
            {
                "evidence_id": f"graph:{index}",
                "source_type": "graph",
                "title": path.get("title") or path.get("relation") or "当前任务图谱路径",
                "summary": summary or "图谱邻居扩展证据",
                "page": None,
                "source": "sqlite_knowledge_graph",
                "source_url": "",
                "license": "project_generated",
                "modality": "graph",
                "confidence": round(float(path.get("confidence") or 0.7), 2),
                "verified": True,
            }
        )
    return evidence


def _operation_chain(equipment: str, sop: dict[str, Any], spatial_guidance: dict[str, Any]) -> list[dict[str, Any]]:
    bindings = spatial_guidance.get("sop_bindings", []) or []
    steps = sop.get("sop_steps", []) or []
    if not bindings:
        bindings = [
            {"step_index": index, "step": step, "component_key": ""}
            for index, step in enumerate(steps, start=1)
        ]
    chain = []
    for item in bindings:
        model_key = str(item.get("component_key") or "")
        chain.append(
            {
                "step_id": f"S{int(item.get('step_index') or len(chain) + 1):02d}",
                "step_index": int(item.get("step_index") or len(chain) + 1),
                "action": item.get("step") or (steps[len(chain)] if len(chain) < len(steps) else ""),
                "component_key": canonical_component_key(equipment, model_key) if model_key else "",
                "model_component_key": model_key,
                "phase": item.get("phase", "作业步骤"),
                "risk_control": item.get("risk_control", "按引用证据执行并拍照留痕"),
                "safety_gate_id": "pre_job_safety_gate" if int(item.get("step_index") or 1) == 1 else "step_evidence_check",
                "status": "blocked" if int(item.get("step_index") or 1) == 1 and (spatial_guidance.get("safety_gate") or {}).get("status") == "blocked" else "ready",
            }
        )
    return chain


def _alignment_status(
    evidence_chain: list[dict[str, Any]],
    component_keys: list[str],
    operation_chain: list[dict[str, Any]],
    safety_gate: dict[str, Any],
) -> str:
    if safety_gate.get("status") == "blocked":
        return "blocked"
    if evidence_chain and component_keys and operation_chain:
        return "complete"
    if evidence_chain or component_keys or operation_chain:
        return "partial"
    return "needs_review"


def build_tri_mro_alignment(
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
) -> dict[str, Any]:
    """Build the evidence-structure-operation alignment object for the UI and reports."""

    evidence_chain: list[dict[str, Any]] = []
    evidence_chain.extend(_evidence_item(index, "manual", item) for index, item in enumerate(citations[:8], start=1))
    evidence_chain.extend(_evidence_item(index, "case", item) for index, item in enumerate(cases[:5], start=1))
    evidence_chain.extend(_graph_evidence(graph_paths))
    evidence_chain.extend(_visual_evidence(visual_asset, image_caption))

    component_keys = workflow_state.get("selected_component_keys", []) or []
    model_component_keys = workflow_state.get("selected_model_component_keys", []) or []
    highlighted = spatial_guidance.get("highlighted_components", []) or []
    confidence_values = [float(item.get("confidence") or 0) for item in highlighted]
    binding_confidence = round(max(confidence_values) if confidence_values else 0, 2)
    maturity = spatial_guidance.get("model_maturity", {}) or {}
    binding_quality = spatial_guidance.get("binding_quality", {}) or {}
    safety_gate = workflow_state.get("safety_gate", {}) or _safety_status(spatial_guidance)
    operation_chain = _operation_chain(equipment, sop, spatial_guidance)
    aligned_steps = sum(1 for item in operation_chain if item.get("component_key"))
    traceable_claims = 1 if evidence_chain else 0
    tri_chain_coverage = 1.0 if evidence_chain and component_keys and operation_chain else 0.67 if evidence_chain and (component_keys or operation_chain) else 0.0

    return {
        "framework": "Tri-MRO",
        "name": "证据链-结构链-作业链三重对齐",
        "alignment_status": _alignment_status(evidence_chain, component_keys, operation_chain, safety_gate),
        "claim": {
            "text": sop.get("diagnosis", text),
            "query": text,
            "traceability": {
                "evidence_count": len(evidence_chain),
                "component_count": len(component_keys),
                "operation_step_count": len(operation_chain),
                "traceable_claims": traceable_claims,
            },
        },
        "evidence_chain": evidence_chain,
        "structure_chain": {
            "equipment": equipment,
            "model": model,
            "component_keys": component_keys,
            "model_component_keys": model_component_keys,
            "cad_model_id": spatial_guidance.get("model_id", ""),
            "cad_model_title": spatial_guidance.get("model_title", ""),
            "binding_level": maturity.get("level", "unknown"),
            "binding_label": maturity.get("label", ""),
            "binding_mode": binding_quality.get("binding_mode") or maturity.get("binding_mode", ""),
            "binding_confidence": binding_confidence,
            "object_level_binding": bool(maturity.get("object_level_binding")),
            "exact_cad_face_binding": bool((spatial_guidance.get("node_bindings") or {}).get("exact_cad_face_binding")),
            "requires_manual_calibration": not bool(maturity.get("object_level_binding")),
        },
        "operation_chain": operation_chain,
        "safety_gate": {
            "status": safety_gate.get("status", "needs_confirmation"),
            "label": safety_gate.get("label", "等待安全确认"),
            "missing_items": safety_gate.get("blocking_items", []),
            "decision": safety_gate.get("decision", ""),
            "blocking_policy": "高风险步骤未满足安全前置条件时阻断或转人工复核。",
        },
        "knowledge_governance": {
            "case_status": "draft",
            "work_order_lifecycle": "当前任务可生成作业票/工单，提交审核后进入案例库、图谱和检索索引。",
            "review_required": True,
            "version": 1,
            "rollback_supported": True,
        },
        "metrics": {
            "traceability_rate": traceable_claims,
            "tri_chain_coverage": round(tri_chain_coverage, 2),
            "cad_binding_confidence": binding_confidence,
            "operation_binding_rate": round(aligned_steps / max(1, len(operation_chain)), 2),
            "high_risk_blocking_ready": safety_gate.get("status") in {"ready", "blocked", "needs_confirmation", "warning"},
        },
        "next_actions": [
            "复核证据链是否覆盖关键结论。",
            "在 CAD 工位确认结构链部件锚点。",
            "按作业票完成安全闸门确认后再执行高风险步骤。",
            "检修完成后生成案例并提交审核。",
        ],
    }
