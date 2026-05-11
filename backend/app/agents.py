from __future__ import annotations

from .compliance import compliance_check, risk_level
from .retrieval import EQUIPMENT_LABELS, RetrievalHit


def build_sop(
    query: str,
    equipment: str,
    maintenance_level: str,
    manual_hits: list[RetrievalHit],
    case_hits: list[RetrievalHit],
) -> dict:
    fault_types = [hit.fault_type for hit in manual_hits + case_hits]
    primary_fault = fault_types[0] if fault_types else "待确认故障"
    equipment_label = EQUIPMENT_LABELS.get(equipment, "设备")

    steps = [
        f"确认设备对象为{equipment_label}，记录型号、运行时长、报警信息和故障现象。",
        "执行停机、断电、验电、挂牌和上锁，释放压力、温度和旋转惯性等残余能量。",
        "佩戴护目镜、防割手套、安全鞋等 PPE，准备拆装工具、测温仪、测振仪、备件和清洁耗材。",
        f"按{maintenance_level or '二级检修'}要求检查与“{primary_fault}”相关的部件，优先核对检修手册引用段落。",
        "对可疑部件进行外观、间隙、润滑、同轴度、泄漏或绝缘检查，并拍照留存。",
        "根据检查结果执行清洗、调整、紧固、补脂或更换备件；任何异常处置需由负责人复核。",
        "复装后进行空载点动和带载试运行，记录温升、振动、噪声、压力、流量和泄漏情况。",
        "形成检修报告，经审核后沉淀为案例并更新知识图谱。",
    ]

    if equipment == "pump":
        steps.insert(3, "隔离泵入口和出口阀门，确认介质泄压、排液完成并设置防滑警示。")
        steps.append("复测出口压力、流量、泄漏点和振动值，确认泵组运行恢复稳定。")
    if equipment == "motor":
        steps.insert(3, "检查接地和绝缘状态，禁止绝缘不合格时强行启动。")
    if equipment == "bearing":
        steps.insert(3, "轴承拆装区域保持清洁，禁止直接硬敲滚道和保持架。")

    possible_causes = []
    for hit in manual_hits + case_hits:
        cause = f"{hit.component}相关：{hit.fault_type}"
        if cause not in possible_causes:
            possible_causes.append(cause)
    if not possible_causes:
        possible_causes = ["检索证据不足，需要补充设备型号、图片或运行参数。"]

    compliance = compliance_check(equipment, steps)
    risk = risk_level(equipment, query, fault_types)
    return {
        "diagnosis": f"系统判断该问题优先按“{primary_fault}”处理，并建议结合引用手册和相似案例复核。",
        "possible_causes": possible_causes[:5],
        "sop_steps": steps,
        "tools_and_parts": infer_tools_parts(equipment, primary_fault, case_hits),
        "acceptance": [
            "验收：试运行 15-30 分钟，无异常噪声、无泄漏、无报警。",
            "复测温升、振动、压力或流量数据，确认满足现场工艺要求。",
            "验收记录、检修图片证据和更换备件编号完整归档。",
        ],
        "risk_level": risk,
        "human_review_required": risk != "low",
        "compliance": [item.__dict__ for item in compliance],
    }


def infer_tools_parts(equipment: str, primary_fault: str, case_hits: list[RetrievalHit]) -> list[str]:
    parts = []
    for hit in case_hits:
        if "备件：" in hit.content:
            parts.append(hit.content.split("备件：", 1)[-1].rstrip("。"))
    if parts:
        return parts[:3]
    if equipment == "pump":
        return ["机械密封组件", "O 形圈", "垫片", "压力表", "扭矩扳手"]
    if equipment == "motor":
        return ["轴承", "润滑脂", "绝缘电阻表", "测振仪", "拉马"]
    if equipment == "bearing":
        return ["同规格轴承", "卡簧钳", "清洗剂", "塞尺", "润滑脂"]
    return ["常用拆装工具", "测温仪", "测振仪", "备件清单"]


def agent_trace(has_image: bool, manual_hits: list[RetrievalHit], case_hits: list[RetrievalHit]) -> list[dict]:
    return [
        {
            "agent": "视觉 Agent",
            "status": "done" if has_image else "skipped",
            "message": "已生成图片结构化描述并参与检索" if has_image else "本次未上传故障图片",
        },
        {
            "agent": "检索 Agent",
            "status": "done",
            "message": f"命中 {len(manual_hits)} 条手册证据和 {len(case_hits)} 条相似案例",
        },
        {
            "agent": "机械诊断 Agent",
            "status": "done",
            "message": "按设备-部件-故障关系归并可能原因",
        },
        {
            "agent": "SOP Agent",
            "status": "done",
            "message": "已生成步骤化作业指引、工具备件和验收标准",
        },
        {
            "agent": "合规审查 Agent",
            "status": "done",
            "message": "已检查 LOTO、PPE、残余能量、工具备件和验收记录",
        },
    ]


def _average_confidence(hits: list[RetrievalHit]) -> float:
    if not hits:
        return 0.0
    return round(sum(hit.confidence for hit in hits) / len(hits), 2)


def agent_trace(
    has_image: bool,
    manual_hits: list[RetrievalHit],
    case_hits: list[RetrievalHit],
    sop: dict | None = None,
    equipment: str = "",
    image_caption: str = "",
) -> list[dict]:
    """Return a UI-ready trace for the multi-agent workflow."""

    all_hits = manual_hits + case_hits
    top_sources = [
        {"title": hit.title, "type": hit.source_type, "confidence": hit.confidence}
        for hit in all_hits[:3]
    ]
    sop_steps = len((sop or {}).get("sop_steps", []))
    compliance_items = len((sop or {}).get("compliance", []))
    risk = (sop or {}).get("risk_level", "unknown")
    review_required = bool((sop or {}).get("human_review_required", True))
    retrieval_confidence = _average_confidence(all_hits)

    return [
        {
            "id": "vision",
            "agent": "视觉 Agent",
            "status": "done" if has_image else "skipped",
            "input": "故障图片" if has_image else "未上传图片",
            "output": image_caption if has_image else "本次仅使用文本、设备型号和知识库检索。",
            "message": "已生成图片结构化描述并参与检索" if has_image else "本次未上传故障图片",
            "evidence": {"has_image": has_image, "caption_length": len(image_caption or "")},
            "confidence": 0.86 if has_image else 0.0,
            "duration_ms": 180 if has_image else 0,
            "next_action": "将视觉标签并入检索查询" if has_image else "可上传故障图片增强跨模态匹配",
        },
        {
            "id": "retrieval",
            "agent": "检索 Agent",
            "status": "done",
            "input": f"{EQUIPMENT_LABELS.get(equipment, equipment or '设备')} / 文本 / 型号 / 图片标签",
            "output": f"命中 {len(manual_hits)} 条手册证据和 {len(case_hits)} 条相似案例。",
            "message": f"命中 {len(manual_hits)} 条手册证据和 {len(case_hits)} 条相似案例",
            "evidence": {
                "manual_hits": len(manual_hits),
                "case_hits": len(case_hits),
                "top_sources": top_sources,
            },
            "confidence": retrieval_confidence,
            "duration_ms": 95 + 8 * len(all_hits),
            "next_action": "交给机械诊断 Agent 归因并排序",
        },
        {
            "id": "diagnosis",
            "agent": "机械诊断 Agent",
            "status": "done",
            "input": "设备-部件-故障证据链",
            "output": "已归纳可能原因、主故障方向和风险等级。",
            "message": "按设备-部件-故障关系归并可能原因",
            "evidence": {"risk_level": risk, "possible_causes": len((sop or {}).get("possible_causes", []))},
            "confidence": max(0.45, retrieval_confidence),
            "duration_ms": 120,
            "next_action": "生成标准化检修作业步骤",
        },
        {
            "id": "sop",
            "agent": "SOP Agent",
            "status": "done",
            "input": "故障判断、检修等级、工具备件和验收要求",
            "output": f"已生成 {sop_steps} 个作业步骤、工具备件和验收标准。",
            "message": "已生成步骤化作业指引、工具备件和验收标准",
            "evidence": {"sop_steps": sop_steps, "acceptance_items": len((sop or {}).get("acceptance", []))},
            "confidence": 0.9 if sop_steps >= 6 else 0.65,
            "duration_ms": 160,
            "next_action": "交给合规审查 Agent 检查安全项",
        },
        {
            "id": "compliance",
            "agent": "合规审查 Agent",
            "status": "done",
            "input": "SOP 步骤和安全规则库",
            "output": f"已检查 {compliance_items} 个安全合规项，风险等级为 {risk}。",
            "message": "已检查 LOTO、PPE、残余能量、工具备件和验收记录",
            "evidence": {"compliance_items": compliance_items, "human_review_required": review_required},
            "confidence": 0.92 if compliance_items >= 5 else 0.7,
            "duration_ms": 110,
            "next_action": "输出可执行方案并等待人工确认",
        },
        {
            "id": "knowledge_update",
            "agent": "知识更新 Agent",
            "status": "pending_review" if review_required else "ready",
            "input": "本次问诊、引用证据、人工修正和现场案例",
            "output": "支持人工修正或案例审核通过后写入案例库、反馈库和知识图谱。",
            "message": "等待人工确认后沉淀为案例或反馈记录",
            "evidence": {"feedback_ready": True, "case_review_required": True},
            "confidence": 0.88,
            "duration_ms": 80,
            "next_action": "提交人工修正或新增案例后更新检索闭环",
        },
    ]


def build_model_review_prompt(query: str, sop: dict, manual_hits: list[RetrievalHit], case_hits: list[RetrievalHit]) -> tuple[str, str, str]:
    evidence_lines = []
    for hit in manual_hits[:5]:
        evidence_lines.append(
            f"- 手册《{hit.title}》P{hit.page} {hit.section}：{hit.content}"
        )
    for hit in case_hits[:3]:
        evidence_lines.append(f"- 案例《{hit.title}》：{hit.content}")

    compliance_lines = [
        f"- {item['label']}：{'通过' if item['passed'] else '需补充'}"
        for item in sop["compliance"]
    ]
    system = (
        "你是工业设备检修专家和安全合规审查员。"
        "你只能基于给定证据复核方案，不要编造未引用的厂家参数。"
        "输出中文，结构为：复核结论、关键风险、建议补充、是否可执行。"
    )
    user = "\n".join(
        [
            f"用户问题：{query}",
            "检索证据：",
            "\n".join(evidence_lines) or "- 无",
            "当前 SOP：",
            "\n".join(f"{index + 1}. {step}" for index, step in enumerate(sop["sop_steps"])),
            "合规检查：",
            "\n".join(compliance_lines),
        ]
    )
    fallback = (
        "复核结论：当前方案已基于手册和案例生成，可作为现场检修辅助方案，但高风险作业仍需负责人复核。\n"
        f"关键风险：风险等级为{sop['risk_level']}，需重点确认停机断电挂牌、PPE、残余能量释放和验收记录。\n"
        "建议补充：补充现场实测温度、振动、压力/流量、电流或泄漏照片，并记录更换备件编号。\n"
        f"是否可执行：{'需要人工复核后执行' if sop['human_review_required'] else '可按流程执行并归档'}。"
    )
    return system, user, fallback
