from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComplianceItem:
    code: str
    label: str
    required: bool
    passed: bool
    evidence: str


BASE_RULES = [
    ("LOTO", "停机、断电、验电、挂牌和上锁"),
    ("PPE", "护目镜、防割手套、安全鞋等个人防护"),
    ("ENERGY", "压力、温度、旋转惯性和残余能量释放"),
    ("TOOLS", "工具、量具、备件和耗材确认"),
    ("ACCEPTANCE", "空载/带载试运行、温升、振动、泄漏等验收记录"),
]

PUMP_RULES = [("MEDIUM", "隔离介质，确认泄压、排液和防滑措施")]
MOTOR_RULES = [("INSULATION", "电机检修前后进行绝缘和接地状态确认")]
BEARING_RULES = [("CLEAN", "轴承拆装保持清洁，禁止硬敲滚道和保持架")]
ENGINE_RULES = [("IGNITION", "发动机检修前确认冷机、断开点火或喷油连接并防止误启动")]

RULE_KEYWORDS = {
    "IGNITION": ["冷机", "点火", "喷油", "误启动"],
    "INSULATION": ["绝缘", "接地"],
    "MEDIUM": ["隔离", "泄压", "排液", "防滑"],
    "CLEAN": ["清洁", "硬敲", "滚道", "保持架"],
}


def compliance_check(equipment: str, sop_steps: list[str]) -> list[ComplianceItem]:
    text = " ".join(sop_steps)
    rules = list(BASE_RULES)
    if equipment == "pump":
        rules += PUMP_RULES
    if equipment == "motor":
        rules += MOTOR_RULES
    if equipment == "bearing":
        rules += BEARING_RULES
    if equipment == "engine":
        rules += ENGINE_RULES

    items: list[ComplianceItem] = []
    for code, label in rules:
        keywords = RULE_KEYWORDS.get(
            code,
            [part for part in label.replace("、", " ").replace("，", " ").split() if part],
        )
        passed = any(keyword in text for keyword in keywords[:4])
        items.append(
            ComplianceItem(
                code=code,
                label=label,
                required=True,
                passed=passed,
                evidence="SOP 已覆盖" if passed else "SOP 需补充该合规项",
            )
        )
    return items


def risk_level(equipment: str, query: str, fault_types: list[str]) -> str:
    text = " ".join([equipment, query, *fault_types])
    if any(word in text for word in ["泄漏", "压力", "高温", "绝缘", "消防", "有毒", "燃油", "喷油", "点火"]):
        return "high"
    if any(word in text for word in ["过热", "振动", "剥落", "汽蚀", "异响", "火花塞", "压缩压力", "气缸"]):
        return "medium"
    return "low"
