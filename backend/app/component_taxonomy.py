from __future__ import annotations

from typing import Any


CANONICAL_COMPONENTS: dict[str, dict[str, dict[str, Any]]] = {
    "bearing": {
        "inner_ring": {"label": "内圈", "aliases": ["内圈", "内滚道"]},
        "outer_ring": {"label": "外圈", "aliases": ["外圈", "外滚道", "滚道"]},
        "rolling_elements": {"label": "滚动体", "aliases": ["滚动体", "钢球", "滚子"]},
        "cage": {"label": "保持架", "aliases": ["保持架"]},
        "seal": {"label": "密封件", "aliases": ["密封", "密封圈", "seal_pair"]},
    },
    "pump": {
        "casing": {"label": "泵体", "aliases": ["泵壳", "泵体"]},
        "impeller": {"label": "叶轮", "aliases": ["叶轮"]},
        "shaft": {"label": "泵轴", "aliases": ["轴", "pump_shaft"]},
        "mechanical_seal": {"label": "机械密封", "aliases": ["机械密封", "密封端", "pump_seal_zone"]},
        "bearing": {"label": "轴承", "aliases": ["轴承", "bearing_seat"]},
        "inlet": {"label": "入口", "aliases": ["入口", "吸入口"]},
        "outlet": {"label": "出口", "aliases": ["出口", "排出口"]},
    },
    "motor": {
        "stator": {"label": "定子", "aliases": ["定子", "绕组"]},
        "rotor": {"label": "转子", "aliases": ["转子"]},
        "shaft": {"label": "转轴", "aliases": ["轴", "motor_shaft"]},
        "end_shield": {"label": "端盖", "aliases": ["端盖", "end_cover"]},
        "bearing": {"label": "轴承", "aliases": ["轴承", "轴承端", "front_bearing_end"]},
        "terminal_box": {"label": "接线盒", "aliases": ["接线盒", "terminal"]},
        "cooling_fan": {"label": "冷却风扇", "aliases": ["风扇", "冷却风扇"]},
    },
    "engine": {
        "spark_plug": {"label": "火花塞", "aliases": ["火花塞"]},
        "cylinder_head": {"label": "气缸盖", "aliases": ["气缸盖", "缸盖", "cooling_fins", "radiator", "cooling_assembly"]},
        "piston": {"label": "活塞", "aliases": ["活塞"]},
        "valve": {"label": "气门", "aliases": ["气门", "进气门", "排气门"]},
        "crankshaft": {"label": "曲轴", "aliases": ["曲轴"]},
        "starter_motor": {"label": "起动电机", "aliases": ["起动电机", "starter"]},
        "water_pump": {"label": "水泵", "aliases": ["水泵"]},
    },
}


DIRECT_ALIASES: dict[tuple[str, str], str] = {
    ("bearing", "seal_pair"): "seal",
    ("pump", "pump_seal_zone"): "mechanical_seal",
    ("pump", "pump_shaft"): "shaft",
    ("motor", "front_bearing_end"): "bearing",
    ("motor", "end_cover"): "end_shield",
    ("engine", "cylinder_block"): "cylinder_head",
    ("engine", "cooling_fins"): "cylinder_head",
}


def _normalize(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def canonical_component_key(equipment: str, raw_key: str) -> str:
    equipment_id = _normalize(equipment) or "general"
    raw = _normalize(raw_key)
    if not raw:
        return f"{equipment_id}.unknown"
    if raw.startswith(f"{equipment_id}."):
        return raw

    mapped = DIRECT_ALIASES.get((equipment_id, raw), raw)
    components = CANONICAL_COMPONENTS.get(equipment_id, {})
    if mapped in components:
        return f"{equipment_id}.{mapped}"

    for component_id, meta in components.items():
        aliases = {_normalize(item) for item in meta.get("aliases", [])}
        if raw in aliases or mapped in aliases:
            return f"{equipment_id}.{component_id}"

    return f"{equipment_id}.{mapped}"


def component_label(equipment: str, canonical_key: str) -> str:
    equipment_id = _normalize(equipment)
    component_id = canonical_key.split(".", 1)[-1]
    return CANONICAL_COMPONENTS.get(equipment_id, {}).get(component_id, {}).get("label", component_id)


def component_confidence_status(confidence: float) -> str:
    if confidence >= 0.60:
        return "done"
    if confidence >= 0.40:
        return "needs_confirmation"
    return "needs_review"


def canonicalize_highlighted_components(equipment: str, highlighted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in highlighted:
        canonical = canonical_component_key(equipment, str(item.get("component_key", "")))
        confidence = float(item.get("confidence") or 0)
        items.append(
            {
                **item,
                "model_component_key": item.get("component_key", ""),
                "canonical_component_key": canonical,
                "canonical_label": component_label(equipment, canonical),
                "grounding_status": component_confidence_status(confidence),
            }
        )
    return items
