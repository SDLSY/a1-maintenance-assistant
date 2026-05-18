from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_3D = ROOT / "data" / "3d"
STANDARD_MODELS = DATA_3D / "standard_models.json"
AUTHORIZED_ROOT = DATA_3D / "authorized_models"
SEMANTIC_SIDECARS = DATA_3D / "semantic_sidecars"
REPORT = DATA_3D / "component_semantics_audit.json"

METADATA_BINDING_KEYS = {
    "binding_mode",
    "cad_mesh",
    "semantic_sidecar_ready",
    "object_level_binding",
    "exact_cad_face_binding",
}

ALLOWED_CANONICAL_KEYS = {
    "bearing": {
        "outer_ring",
        "inner_ring",
        "rolling_elements",
        "cage",
        "seal_pair",
    },
    "motor": {
        "front_bearing_end",
        "end_cover",
        "output_shaft",
        "motor_housing",
        "terminal_connector",
        "mounting_flange",
    },
    "pump": {
        "pump_seal_zone",
        "pump_head",
        "pump_shaft",
        "motor_body",
        "inlet_outlet",
        "mounting_bracket",
        "impeller",
        "pump_casing",
    },
    "engine": {
        "spark_plug",
        "cylinder_head",
        "cylinder_block",
        "crankcase",
        "cooling_fins",
        "intake_exhaust_ports",
        "wiring_harness",
        "starter_motor",
        "water_pump",
    },
}

DEPRECATED_PRIMARY_KEYS = {
    "front_bearing": "front_bearing_end",
    "mechanical_seal": "pump_seal_zone",
    "radiator": "cooling_fins",
    "intake_exhaust": "intake_exhaust_ports",
    "rotor_shaft": "output_shaft",
    "stator_housing": "motor_housing",
    "stator_winding": "motor_housing",
    "cylinder": "cylinder_head/cylinder_block",
    "seal_lubrication": "seal_pair",
}

REQUIRED_ALIAS_FOR_REPLACEMENT = {
    "front_bearing_end": "front_bearing",
    "pump_seal_zone": "mechanical_seal",
    "cooling_fins": "radiator",
    "intake_exhaust_ports": "intake_exhaust",
    "output_shaft": "rotor_shaft",
    "motor_housing": "stator_housing",
    "cylinder_head": "cylinder",
    "seal_pair": "seal_lubrication",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def issue(level: str, path: Path, message: str, *, key: str = "") -> dict[str, Any]:
    return {
        "level": level,
        "path": path.relative_to(ROOT).as_posix(),
        "key": key,
        "message": message,
    }


def is_blank(value: Any) -> bool:
    return not str(value or "").strip()


def check_component_key(
    errors: list[dict[str, Any]],
    path: Path,
    equipment: str,
    key: str,
    context: str,
) -> None:
    if key in DEPRECATED_PRIMARY_KEYS:
        errors.append(
            issue(
                "error",
                path,
                f"{context} uses deprecated primary key '{key}', use '{DEPRECATED_PRIMARY_KEYS[key]}' as canonical key",
                key=key,
            )
        )
    allowed = ALLOWED_CANONICAL_KEYS.get(equipment, set())
    if allowed and key not in allowed:
        errors.append(issue("error", path, f"{context} uses unknown canonical key '{key}' for {equipment}", key=key))


def check_semantic_item(
    errors: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    path: Path,
    equipment: str,
    key: str,
    label: str,
    aliases: list[str],
    manual_keywords: list[str],
    context: str,
) -> None:
    check_component_key(errors, path, equipment, key, context)
    if is_blank(label):
        errors.append(issue("error", path, f"{context} '{key}' has blank label", key=key))
    if not manual_keywords:
        warnings.append(issue("warning", path, f"{context} '{key}' has no manual_keywords", key=key))
    required_alias = REQUIRED_ALIAS_FOR_REPLACEMENT.get(key)
    if required_alias and required_alias not in aliases and required_alias not in manual_keywords:
        errors.append(
            issue(
                "error",
                path,
                f"{context} '{key}' should keep legacy term '{required_alias}' as alias or keyword for compatibility",
                key=key,
            )
        )


def check_sidecar(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    sidecar = read_json(path)
    equipment = sidecar.get("equipment", "")

    part_ids = {item.get("id", "") for item in sidecar.get("part_semantics", [])}
    component_ids = {item.get("component_key", "") for item in sidecar.get("components", [])}
    known_ids = part_ids | component_ids

    for item in sidecar.get("part_semantics", []):
        key = item.get("id", "")
        check_semantic_item(
            errors,
            warnings,
            path,
            equipment,
            key,
            item.get("label", ""),
            list(item.get("aliases", [])),
            list(item.get("manual_keywords", [])),
            "part_semantics.id",
        )

    for item in sidecar.get("components", []):
        key = item.get("component_key", "")
        check_semantic_item(
            errors,
            warnings,
            path,
            equipment,
            key,
            item.get("label", ""),
            list(item.get("aliases", [])),
            list(item.get("manual_keywords", [])),
            "components.component_key",
        )

    bindings = sidecar.get("node_bindings", {})
    if isinstance(bindings, dict):
        for key in bindings:
            if key in METADATA_BINDING_KEYS:
                continue
            check_component_key(errors, path, equipment, key, "node_bindings key")
            if known_ids and key not in known_ids:
                errors.append(issue("error", path, f"node_bindings key '{key}' is not present in component semantics", key=key))

    for view in sidecar.get("inspection_views", []):
        for key in view.get("focus_components", []):
            check_component_key(errors, path, equipment, key, f"inspection_view '{view.get('id', '')}' focus")
            if known_ids and key not in known_ids:
                errors.append(
                    issue(
                        "error",
                        path,
                        f"inspection_view '{view.get('id', '')}' focuses unknown component '{key}'",
                        key=key,
                    )
                )
    return errors, warnings


def check_standard_models() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    manifest = read_json(STANDARD_MODELS)
    for model in manifest.get("models", []):
        equipment = model.get("equipment", "")
        for item in model.get("components", []):
            key = item.get("component_key", "")
            check_semantic_item(
                errors,
                warnings,
                STANDARD_MODELS,
                equipment,
                key,
                item.get("label", ""),
                list(item.get("aliases", [])),
                list(item.get("manual_keywords", [])),
                f"standard model '{model.get('id', '')}' component",
            )
    return errors, warnings


def audit() -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    standard_errors, standard_warnings = check_standard_models()
    errors.extend(standard_errors)
    warnings.extend(standard_warnings)

    for path in sorted([*AUTHORIZED_ROOT.glob("*/*.sidecar.json"), *SEMANTIC_SIDECARS.glob("*.sidecar.json")]):
        sidecar_errors, sidecar_warnings = check_sidecar(path)
        errors.extend(sidecar_errors)
        warnings.extend(sidecar_warnings)

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "passed" if not errors else "failed",
        "policy": {
            "allowed_canonical_keys": {key: sorted(value) for key, value in ALLOWED_CANONICAL_KEYS.items()},
            "deprecated_primary_keys": DEPRECATED_PRIMARY_KEYS,
        },
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
