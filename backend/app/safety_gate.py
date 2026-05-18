from __future__ import annotations

from datetime import datetime
from typing import Any


GATE_LABELS = {
    "power_locked_out": "断电挂牌",
    "zero_voltage_verified": "验电/零能量确认",
    "pressure_released": "泄压确认",
    "temperature_safe": "温度安全",
    "ppe_confirmed": "PPE确认",
    "tool_checked": "工具备件确认",
    "cleanliness_confirmed": "清洁度确认",
    "engine_cold": "发动机冷机",
    "ignition_disabled": "点火/喷油断开",
}


def _gate_passed(gate: str, text: str, sop_text: str) -> bool:
    corpus = f"{text} {sop_text}"
    checks = {
        "power_locked_out": ["断电", "挂牌", "上锁", "停机"],
        "zero_voltage_verified": ["验电", "零能量", "接地"],
        "pressure_released": ["泄压", "压力释放", "排液", "隔离介质"],
        "temperature_safe": ["冷却", "降温", "温度", "冷机"],
        "ppe_confirmed": ["PPE", "护目", "手套", "防护", "安全鞋"],
        "tool_checked": ["工具", "量具", "备件", "O形圈", "密封"],
        "cleanliness_confirmed": ["清洁", "洁净", "污染"],
        "engine_cold": ["冷机", "冷却", "降温"],
        "ignition_disabled": ["点火", "喷油", "误启动"],
    }
    return any(word in corpus for word in checks.get(gate, []))


def build_safety_gate_state(
    *,
    text: str,
    risk_level: str,
    required_gates: list[str],
    sop_steps: list[str],
    evidence_decision: str,
) -> dict[str, Any]:
    sop_text = " ".join(sop_steps or [])
    direct_disassembly = any(word in text for word in ["直接拆", "直接打开", "直接拆卸", "强行拆", "能不能直接"])
    gate_status = {gate: _gate_passed(gate, text, sop_text) for gate in required_gates}
    missing = [GATE_LABELS.get(gate, gate) for gate, passed in gate_status.items() if not passed]
    high_risk = risk_level == "high" or direct_disassembly
    if evidence_decision == "refuse":
        state = "NEED_REVIEW"
        decision = "证据不足，不允许输出确定检修结论，需补充资料或人工复核。"
    elif high_risk and (missing or direct_disassembly):
        state = "BLOCKED"
        decision = "高风险步骤未满足安全前置条件，系统阻断拆卸或进入下一步作业。"
    elif missing:
        state = "WAITING_SAFETY_CHECK"
        decision = "存在未确认安全项，需人工确认后继续。"
    else:
        state = "READY"
        decision = "安全闸门已满足，可进入受控检修步骤。"
    return {
        "state": state,
        "status": state.lower(),
        "required_gates": required_gates,
        "gate_status": gate_status,
        "missing_items": missing,
        "block_reason": missing if state == "BLOCKED" else [],
        "decision": decision,
        "audit_log": [
            {
                "time": datetime.utcnow().isoformat(timespec="seconds"),
                "actor": "system",
                "event": state.lower(),
                "reason": decision,
            }
        ],
    }


def attach_step_gates(steps: list[dict[str, Any]], gate_state: dict[str, Any], risk_level: str) -> list[dict[str, Any]]:
    enriched = []
    for index, step in enumerate(steps, start=1):
        high_risk_step = index == 1 or risk_level == "high" or any(word in str(step.get("action", "")) for word in ["拆", "打开", "吊装"])
        status = gate_state["state"] if high_risk_step else "READY"
        enriched.append(
            {
                **step,
                "risk_level": "high" if high_risk_step else risk_level,
                "required_gates": gate_state["required_gates"] if high_risk_step else [],
                "gate_status": gate_state["gate_status"] if high_risk_step else {},
                "decision": "blocked" if status == "BLOCKED" else "needs_review" if status == "NEED_REVIEW" else "ready",
                "block_reason": gate_state["block_reason"] if status == "BLOCKED" else [],
            }
        )
    return enriched
