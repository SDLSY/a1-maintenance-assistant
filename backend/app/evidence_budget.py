from __future__ import annotations

from typing import Any


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _manual_score(citations: list[dict[str, Any]]) -> float:
    if not citations:
        return 0.0
    confidence = max(float(item.get("confidence") or 0) for item in citations)
    count_bonus = min(0.35, len(citations) * 0.12)
    source_bonus = 0.12 if any(item.get("source") or item.get("source_url") for item in citations) else 0.0
    return _clamp(max(confidence, 0.45) + count_bonus + source_bonus)


def _case_score(cases: list[dict[str, Any]]) -> float:
    if not cases:
        return 0.0
    confidence = max(float(item.get("confidence") or 0) for item in cases)
    return _clamp(max(confidence, 0.4) + min(0.25, len(cases) * 0.1))


def _graph_score(graph_paths: list[dict[str, Any]]) -> float:
    if not graph_paths:
        return 0.0
    confidence = max(float(item.get("confidence") or 0.65) for item in graph_paths)
    return _clamp(confidence + min(0.2, len(graph_paths) * 0.06))


def _visual_score(visual_asset: dict[str, Any] | None, image_caption: str) -> float:
    if visual_asset:
        analysis = visual_asset.get("analysis") or {}
        labels = analysis.get("defect_labels") or []
        return _clamp(0.62 + min(0.22, len(labels) * 0.04))
    if image_caption:
        return 0.48
    return 0.0


def build_evidence_budget(
    *,
    citations: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    graph_paths: list[dict[str, Any]],
    visual_asset: dict[str, Any] | None,
    image_caption: str,
    model: str,
) -> dict[str, Any]:
    source_scores = {
        "manual": round(_manual_score(citations), 3),
        "case": round(_case_score(cases), 3),
        "graph": round(_graph_score(graph_paths), 3),
        "visual": round(_visual_score(visual_asset, image_caption), 3),
    }
    score = (
        0.35 * source_scores["manual"]
        + 0.25 * source_scores["case"]
        + 0.20 * source_scores["graph"]
        + 0.20 * source_scores["visual"]
    )
    if str(model or "").upper().startswith("UNKNOWN"):
        score = min(score, 0.56)
    score = round(_clamp(score), 3)
    if score >= 0.75:
        decision = "answer"
        confidence_level = "high"
        label = "证据充足，可输出明确判断"
    elif score >= 0.50:
        decision = "confirm"
        confidence_level = "medium"
        label = "证据基本可用，需要人工确认"
    elif score >= 0.30:
        decision = "direction_only"
        confidence_level = "low"
        label = "证据不足，只输出排查方向"
    else:
        decision = "refuse"
        confidence_level = "insufficient"
        label = "证据不足，拒绝确定性判断"
    missing = []
    if source_scores["manual"] < 0.35:
        missing.append("匹配设备型号的维修手册证据")
    if source_scores["case"] < 0.30:
        missing.append("相似已审核检修案例")
    if source_scores["graph"] < 0.30:
        missing.append("设备-部件-故障图谱路径")
    if source_scores["visual"] < 0.30:
        missing.append("清晰现场图片或已审核视觉证据")
    return {
        "score": score,
        "source_scores": source_scores,
        "decision": decision,
        "confidence_level": confidence_level,
        "label": label,
        "missing_evidence": missing,
        "supplement_suggestions": [
            "补充设备铭牌或型号",
            "补充故障部位近距离清晰图片",
            "补充运行温度、压力、振动、持续时间等工况信息",
            "提交人工复核意见后再写入知识库",
        ][: max(1, len(missing))],
    }
