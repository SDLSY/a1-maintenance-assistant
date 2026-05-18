from __future__ import annotations

from typing import Any


FMEA_TEMPLATES: dict[str, dict[str, Any]] = {
    "pump.mechanical_seal": {
        "failure_mode": "机械密封泄漏",
        "possible_causes": ["密封端面磨损", "密封圈老化", "安装偏差", "轴套磨损"],
        "effects": ["介质泄漏", "泵效率下降", "轴承污染", "现场滑倒或介质暴露风险"],
        "severity": 4,
        "occurrence": 3,
        "detectability": 2,
        "recommended_action": "停机隔离后检查机械密封、O形圈、轴套和轴承端状态",
    },
    "pump.bearing": {
        "failure_mode": "泵轴承异响或过热",
        "possible_causes": ["润滑不足", "轴承磨损", "对中不良", "密封泄漏污染润滑脂"],
        "effects": ["振动升高", "轴封失效", "泵效率下降", "轴承抱死风险"],
        "severity": 4,
        "occurrence": 3,
        "detectability": 3,
        "recommended_action": "停机后检查润滑、游隙、温升和振动趋势",
    },
    "bearing.outer_ring": {
        "failure_mode": "轴承外圈滚道剥落",
        "possible_causes": ["疲劳剥落", "污染颗粒压痕", "润滑失效", "装配冲击"],
        "effects": ["异响", "振动升高", "温升", "二次损伤"],
        "severity": 3,
        "occurrence": 3,
        "detectability": 2,
        "recommended_action": "清洁拆检滚道并更换失效轴承，复测振动和温升",
    },
    "bearing.rolling_elements": {
        "failure_mode": "滚动体点蚀或压痕",
        "possible_causes": ["污染", "过载", "润滑不足", "安装冲击"],
        "effects": ["周期性冲击", "噪声升高", "滚道二次损伤"],
        "severity": 3,
        "occurrence": 3,
        "detectability": 2,
        "recommended_action": "检查滚动体和滚道，确认清洁度与润滑状态",
    },
    "motor.bearing": {
        "failure_mode": "电机轴承温升异常",
        "possible_causes": ["润滑不足", "轴承磨损", "端盖配合异常", "对中不良"],
        "effects": ["绝缘老化加速", "振动升高", "转子擦碰风险"],
        "severity": 4,
        "occurrence": 3,
        "detectability": 3,
        "recommended_action": "断电验电后检查轴承、端盖、润滑和对中状态",
    },
    "engine.spark_plug": {
        "failure_mode": "火花塞积碳或间隙异常",
        "possible_causes": ["混合气偏浓", "点火弱", "长期低速运行", "火花塞磨损"],
        "effects": ["冷车启动困难", "怠速不稳", "燃烧不充分"],
        "severity": 2,
        "occurrence": 3,
        "detectability": 2,
        "recommended_action": "冷机断开点火后检查火花塞积碳、间隙和压缩压力",
    },
    "engine.cylinder_head": {
        "failure_mode": "气缸盖密封或散热异常",
        "possible_causes": ["缸垫密封不良", "散热鳍片污堵", "压缩压力不足"],
        "effects": ["启动困难", "过热", "动力下降"],
        "severity": 3,
        "occurrence": 2,
        "detectability": 3,
        "recommended_action": "冷机后检查气缸盖、火花塞孔、压缩压力和散热状态",
    },
}


def build_fmea_risk_chain(component_key: str, risk_level: str, possible_causes: list[str] | None = None) -> dict[str, Any]:
    template = dict(FMEA_TEMPLATES.get(component_key, {}))
    if not template:
        template = {
            "failure_mode": f"{component_key} 相关故障",
            "possible_causes": possible_causes or ["磨损", "安装偏差", "润滑或密封异常"],
            "effects": ["设备性能下降", "故障扩大", "安全风险升高"],
            "severity": 3,
            "occurrence": 2,
            "detectability": 3,
            "recommended_action": "依据手册和案例完成部件检查并记录验收结果",
        }
    if possible_causes:
        merged = []
        for item in list(template.get("possible_causes", [])) + possible_causes:
            if item and item not in merged:
                merged.append(item)
        template["possible_causes"] = merged[:6]
    risk_adjust = {"high": 1, "medium": 0, "low": -1}.get(risk_level, 0)
    template["severity"] = max(1, min(5, int(template["severity"]) + risk_adjust))
    template["occurrence"] = max(1, min(5, int(template["occurrence"])))
    template["detectability"] = max(1, min(5, int(template["detectability"])))
    template["risk_priority"] = template["severity"] * template["occurrence"] * template["detectability"]
    template["method_note"] = "轻量 FMEA 风险链：借鉴故障模式-影响-措施分析思路，不声称符合付费标准全文。"
    return template
