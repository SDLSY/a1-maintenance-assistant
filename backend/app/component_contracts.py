from __future__ import annotations

from typing import Any

from .component_taxonomy import CANONICAL_COMPONENTS, canonical_component_key, component_label


CONTRACT_OVERRIDES: dict[str, dict[str, Any]] = {
    "pump.mechanical_seal": {
        "common_faults": ["泄漏", "密封端面磨损", "密封圈老化", "安装偏差", "轴套磨损"],
        "visual_clues": ["油污", "液体渗漏", "密封端污染", "残液痕迹"],
        "manual_keywords": ["mechanical seal", "seal leakage", "密封端面", "泄漏", "O形圈"],
        "safety_risks": ["残压", "高温介质", "旋转部件", "夹伤", "滑倒"],
        "required_gates": ["power_locked_out", "pressure_released", "temperature_safe", "ppe_confirmed", "tool_checked"],
        "cad_binding": {"type": "semantic_hotspot", "precision_level": "component", "confidence": 0.64},
    },
    "pump.bearing": {
        "common_faults": ["异响", "过热", "润滑不足", "游隙异常"],
        "visual_clues": ["油污", "变色", "磨损", "轴承座污染"],
        "manual_keywords": ["bearing", "lubrication", "轴承", "温升", "振动"],
        "safety_risks": ["残余转动", "夹伤", "高温"],
        "required_gates": ["power_locked_out", "pressure_released", "temperature_safe", "ppe_confirmed"],
        "cad_binding": {"type": "semantic_hotspot", "precision_level": "component", "confidence": 0.58},
    },
    "bearing.outer_ring": {
        "common_faults": ["剥落", "点蚀", "压痕", "滚道磨损"],
        "visual_clues": ["剥落坑", "蓝变", "压痕", "滚道划伤"],
        "manual_keywords": ["outer ring", "spalling", "外圈", "滚道", "剥落"],
        "safety_risks": ["污染", "硬敲滚道", "二次损伤"],
        "required_gates": ["power_locked_out", "ppe_confirmed", "cleanliness_confirmed", "tool_checked"],
        "cad_binding": {"type": "object_anchor", "precision_level": "anchor", "confidence": 0.82},
    },
    "bearing.rolling_elements": {
        "common_faults": ["点蚀", "压痕", "剥落", "卡滞"],
        "visual_clues": ["滚珠压痕", "点蚀", "划伤", "变色"],
        "manual_keywords": ["rolling element", "ball", "roller", "滚动体", "钢球"],
        "safety_risks": ["污染", "硬敲", "零件散落"],
        "required_gates": ["power_locked_out", "ppe_confirmed", "cleanliness_confirmed", "tool_checked"],
        "cad_binding": {"type": "object_anchor", "precision_level": "anchor", "confidence": 0.8},
    },
    "motor.bearing": {
        "common_faults": ["温升", "异响", "润滑不足", "对中不良", "轴承磨损"],
        "visual_clues": ["端盖发热", "油脂污染", "密封老化"],
        "manual_keywords": ["motor bearing", "端盖", "轴承", "温升", "振动"],
        "safety_risks": ["触电", "误启动", "旋转部件", "高温"],
        "required_gates": ["power_locked_out", "zero_voltage_verified", "temperature_safe", "ppe_confirmed", "tool_checked"],
        "cad_binding": {"type": "semantic_hotspot", "precision_level": "component", "confidence": 0.56},
    },
    "motor.shaft": {
        "common_faults": ["弯曲", "对中不良", "磨损", "振动"],
        "visual_clues": ["轴端磨痕", "偏摆", "联轴器异常"],
        "manual_keywords": ["shaft", "alignment", "转轴", "对中", "振动"],
        "safety_risks": ["旋转部件", "夹伤", "误启动"],
        "required_gates": ["power_locked_out", "zero_voltage_verified", "ppe_confirmed", "tool_checked"],
        "cad_binding": {"type": "semantic_hotspot", "precision_level": "component", "confidence": 0.54},
    },
    "engine.spark_plug": {
        "common_faults": ["积碳", "间隙异常", "点火弱", "启动困难"],
        "visual_clues": ["积碳", "电极磨损", "油污", "烧蚀"],
        "manual_keywords": ["spark plug", "火花塞", "间隙", "积碳", "压缩压力"],
        "safety_risks": ["误启动", "高温", "点火系统残余能量"],
        "required_gates": ["engine_cold", "ignition_disabled", "ppe_confirmed", "tool_checked"],
        "cad_binding": {"type": "semantic_hotspot", "precision_level": "component", "confidence": 0.5},
    },
    "engine.cylinder_head": {
        "common_faults": ["压缩压力不足", "密封不良", "散热异常", "启动困难"],
        "visual_clues": ["散热鳍片污堵", "缸盖油污", "垫片渗漏"],
        "manual_keywords": ["cylinder head", "compression pressure", "气缸盖", "压缩压力"],
        "safety_risks": ["高温", "误启动", "夹伤"],
        "required_gates": ["engine_cold", "ignition_disabled", "ppe_confirmed", "tool_checked"],
        "cad_binding": {"type": "semantic_hotspot", "precision_level": "component", "confidence": 0.48},
    },
}


PRECISION_LABELS = {
    "equipment": "设备级识别",
    "component": "部件级绑定",
    "anchor": "对象/锚点级绑定",
    "geometry": "几何/面级绑定",
}


def _default_contract(equipment: str, canonical_key: str) -> dict[str, Any]:
    equipment_id, component_id = canonical_key.split(".", 1) if "." in canonical_key else (equipment, canonical_key)
    meta = CANONICAL_COMPONENTS.get(equipment_id, {}).get(component_id, {})
    aliases = list(meta.get("aliases", []))
    label = component_label(equipment_id, canonical_key)
    return {
        "component_key": canonical_key,
        "label": label,
        "aliases": aliases or [label, component_id],
        "equipment_types": [equipment_id],
        "common_faults": ["异常", "磨损", "泄漏", "异响", "过热"],
        "visual_clues": ["油污", "磨损痕迹", "变色", "裂纹"],
        "manual_keywords": [label, component_id],
        "cad_binding": {"type": "semantic_hotspot", "precision_level": "component", "confidence": 0.45},
        "safety_risks": ["误启动", "夹伤", "高温"],
        "required_gates": ["power_locked_out", "ppe_confirmed", "tool_checked"],
        "sop_templates": [f"{equipment_id}_{component_id}_inspection"],
    }


def get_component_contract(equipment: str, component_key: str) -> dict[str, Any]:
    canonical = canonical_component_key(equipment, component_key)
    contract = _default_contract(equipment, canonical)
    override = CONTRACT_OVERRIDES.get(canonical, {})
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(contract.get(key), dict):
            merged = dict(contract[key])
            merged.update(value)
            contract[key] = merged
        else:
            contract[key] = value
    binding = contract.get("cad_binding", {})
    precision = binding.get("precision_level", "component")
    contract["binding_precision_level"] = precision
    contract["binding_precision_label"] = PRECISION_LABELS.get(precision, precision)
    contract["manual_calibration_required"] = precision not in {"anchor", "geometry"} or binding.get("type") == "semantic_hotspot"
    return contract


def infer_component_contract(
    equipment: str,
    *,
    component_keys: list[str] | None = None,
    model_component_keys: list[str] | None = None,
    text: str = "",
) -> dict[str, Any]:
    candidates = list(component_keys or []) + list(model_component_keys or [])
    normalized_text = str(text or "").lower()
    for candidate in candidates:
        if candidate:
            return get_component_contract(equipment, candidate)
    equipment_id = str(equipment or "").lower()
    if equipment_id == "pump" and any(word in normalized_text for word in ["密封", "seal", "泄漏", "滴漏"]):
        return get_component_contract("pump", "pump.mechanical_seal")
    if equipment_id == "bearing" and any(word in normalized_text for word in ["外圈", "滚道", "剥落", "spalling"]):
        return get_component_contract("bearing", "bearing.outer_ring")
    if equipment_id == "motor" and any(word in normalized_text for word in ["轴承", "温升", "异响", "振动"]):
        return get_component_contract("motor", "motor.bearing")
    if equipment_id == "engine" and any(word in normalized_text for word in ["火花塞", "spark", "启动"]):
        return get_component_contract("engine", "engine.spark_plug")
    first = next(iter(CANONICAL_COMPONENTS.get(equipment_id, {})), "unknown")
    return get_component_contract(equipment_id, f"{equipment_id}.{first}")
