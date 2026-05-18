from __future__ import annotations

from pathlib import Path
from typing import Any


def risk_boundary() -> dict[str, Any]:
    return {
        "not_for_measurement": True,
        "not_for_manufacturing": True,
        "not_for_safety_release": True,
        "allowed_use": ["candidate CAD drafting", "structure-chain grounding", "manual review"],
        "required_gate": "mechanical human review before standard asset promotion",
    }


def file_item(path: Path, *, project_root: Path) -> dict[str, Any]:
    try:
        display_path = str(path.resolve().relative_to(project_root.resolve())).replace("\\", "/")
    except ValueError:
        display_path = str(path)
    return {
        "path": display_path,
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
    }


def build_empty_artifact_manifest() -> dict[str, Any]:
    return {
        "schema_version": "candidate-cad-artifacts-v1",
        "source_files": {
            "cadquery": {"path": "", "exists": False, "bytes": 0},
            "openscad": {"path": "", "exists": False, "bytes": 0},
            "cad_spec": {"path": "", "exists": False, "bytes": 0},
            "observation": {"path": "", "exists": False, "bytes": 0},
        },
        "cad_files": {
            "step": {"path": "", "exists": False, "bytes": 0},
            "stl": {"path": "", "exists": False, "bytes": 0},
            "openscad_stl": {"path": "", "exists": False, "bytes": 0},
            "glb": {"path": "", "exists": False, "bytes": 0},
            "fcstd": {"path": "", "exists": False, "bytes": 0},
        },
        "renders": {
            "front": {"path": "", "exists": False, "bytes": 0},
            "side": {"path": "", "exists": False, "bytes": 0},
            "top": {"path": "", "exists": False, "bytes": 0},
            "iso": {"path": "", "exists": False, "bytes": 0},
        },
        "quality_gates": {
            "human_review_required": True,
            "vlm_compare_required": True,
            "runtime_report_required": True,
            "freecad_validation_required": True,
            "blender_render_required": True,
            "openscad_export_required": True,
        },
        "quality_reports": {
            "freecad_validation": {"path": "", "exists": False, "bytes": 0},
            "blender_render": {"path": "", "exists": False, "bytes": 0},
            "openscad_export": {"path": "", "exists": False, "bytes": 0},
        },
        "render_engine": "unknown",
        "risk_boundary": risk_boundary(),
    }
