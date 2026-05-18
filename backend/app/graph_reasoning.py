from __future__ import annotations

from .retrieval import EQUIPMENT_LABELS, RetrievalHit


SAFETY_BY_FAULT = {
    "泄漏": ["隔离介质", "释放压力", "防滑警示", "试压验收"],
    "汽蚀": ["隔离泵组", "检查入口", "复测流量", "试运行"],
    "过热": ["停机断电", "验电挂牌", "测温复核", "空载试运行"],
    "振动": ["停机断电", "联轴器对中", "复测振动", "试运行"],
    "剥落": ["PPE 防护", "清洁装配区", "禁止敲击滚道", "空载试运行"],
    "火花塞": ["冷机拆装", "清洁火花塞孔", "扭矩复核", "防止误启动"],
    "压缩压力": ["拆下喷油器", "油门全开", "压力表固定", "结果复核"],
    "水泵": ["冷却液释放", "密封检查", "叶轮检查", "泄漏复测"],
}


def _safety_for_fault(fault: str) -> list[str]:
    for key, values in SAFETY_BY_FAULT.items():
        if key in fault:
            return values
    return ["停机断电", "PPE 防护", "人工复核", "验收归档"]


def build_graph_paths(equipment: str, manual_hits: list[RetrievalHit], case_hits: list[RetrievalHit]) -> list[dict]:
    paths: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    equipment_label = EQUIPMENT_LABELS.get(equipment, equipment or "设备")
    for hit in manual_hits + case_hits:
        component = hit.component or "部件"
        fault = hit.fault_type or "待确认故障"
        key = (equipment_label, component, fault)
        if key in seen:
            continue
        seen.add(key)
        paths.append(
            {
                "equipment": equipment_label,
                "component": component,
                "fault": fault,
                "source_title": hit.title,
                "source_type": hit.source_type,
                "confidence": hit.confidence,
                "path": [
                    equipment_label,
                    component,
                    fault,
                    "标准化 SOP",
                    "合规校验",
                ],
                "relations": [
                    "包含部件",
                    "出现故障",
                    "生成作业流程",
                    "执行安全检查",
                ],
                "safety_neighbors": _safety_for_fault(fault),
            }
        )
        if len(paths) >= 5:
            break
    return paths


def build_visual_evidence(
    manual_hits: list[RetrievalHit],
    image_caption: str = "",
    visual_asset: dict | None = None,
) -> list[dict]:
    evidence: list[dict] = []
    if visual_asset:
        analysis = visual_asset.get("analysis", {})
        evidence.append(
            {
                "type": "uploaded_visual_asset",
                "title": visual_asset.get("filename", "用户上传故障图片"),
                "caption": analysis.get("caption", visual_asset.get("caption", "")),
                "source": "现场输入",
                "confidence": max(
                    [item.get("confidence", 0.0) for item in analysis.get("defect_labels", [])]
                    or [0.82]
                ),
                "defect_labels": analysis.get("defect_labels", []),
                "ocr_text": analysis.get("ocr_text", ""),
                "flowchart": analysis.get("flowchart", {}),
            }
        )
    if image_caption:
        evidence.append(
            {
                "type": "uploaded_image_caption",
                "title": "用户上传故障图片",
                "caption": image_caption,
                "source": "现场输入",
                "confidence": 0.86,
            }
        )
    for hit in manual_hits:
        if hit.modality == "image" or hit.image_caption:
            evidence.append(
                {
                    "type": "manual_visual_chunk",
                    "title": hit.title,
                    "caption": hit.image_caption or hit.content[:160],
                    "source": hit.source,
                    "page": hit.page,
                    "confidence": hit.confidence,
                }
            )
    return evidence[:6]
