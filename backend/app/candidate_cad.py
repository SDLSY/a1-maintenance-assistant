from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .cad_pipeline.codegen import cadquery_code, openscad_code
from .cad_pipeline.comparator import compare_candidate_to_observation
from .cad_pipeline.contracts import build_empty_artifact_manifest, file_item, risk_boundary
from .cad_pipeline.renderer import render_candidate_artifacts
from .component_taxonomy import canonical_component_key, component_label
from .database import DATA_DIR, PROJECT_ROOT

CANDIDATE_ROOT = DATA_DIR / "cad_candidates"
ALLOWED_REVIEW_STATUSES = {
    "generated",
    "rendered",
    "vlm_scored",
    "needs_review",
    "approved_candidate",
    "rejected",
    "promoted_standard_asset",
}


def _utc() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _safe_slug(value: str, fallback: str = "cad") -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "").strip()).strip("-").lower()
    return slug[:48] or fallback


def _candidate_score(items: list[dict[str, Any]], default: float = 0.5) -> float:
    scores = [float(item.get("confidence") or 0) for item in items if isinstance(item, dict)]
    return max(scores) if scores else default


def _visual_text(visual_asset: dict[str, Any]) -> str:
    analysis = visual_asset.get("analysis") or {}
    parts = [
        visual_asset.get("filename", ""),
        visual_asset.get("caption", ""),
        analysis.get("caption", ""),
        analysis.get("ocr_text", ""),
        " ".join(str(item.get("label", "")) for item in analysis.get("component_candidates", []) if isinstance(item, dict)),
        " ".join(str(item.get("label", "")) for item in analysis.get("defect_labels", []) if isinstance(item, dict)),
        " ".join(str(item) for item in analysis.get("retrieval_keywords", [])),
    ]
    return " ".join(parts).lower()


def _equipment_from_visual(visual_asset: dict[str, Any], requested: str = "") -> str:
    if requested:
        return requested
    analysis = visual_asset.get("analysis") or {}
    candidates = analysis.get("equipment_candidates") or []
    if candidates and isinstance(candidates[0], dict):
        return str(candidates[0].get("id") or "general")
    return str(visual_asset.get("equipment") or "general")


def _default_component_ids(equipment: str, text: str) -> list[str]:
    if equipment == "bearing":
        keys = ["outer_ring", "rolling_elements", "inner_ring", "cage"]
        if "seal" in text or "密封" in text:
            keys.append("seal")
        return keys
    if equipment == "pump":
        keys = ["casing", "mechanical_seal", "shaft", "bearing"]
        if any(term in text for term in ["impeller", "叶轮", "cavitation"]):
            keys.append("impeller")
        if any(term in text for term in ["inlet", "入口", "suction"]):
            keys.append("inlet")
        if any(term in text for term in ["outlet", "出口", "discharge"]):
            keys.append("outlet")
        return keys
    if equipment == "motor":
        return ["stator", "rotor", "shaft", "end_shield", "bearing", "terminal_box"]
    if equipment == "engine":
        return ["cylinder_head", "spark_plug", "piston", "valve", "crankshaft"]
    return ["unknown"]


def build_cad_observation(visual_asset: dict[str, Any], *, equipment: str = "", model: str = "") -> dict[str, Any]:
    analysis = visual_asset.get("analysis") or {}
    equipment_id = _equipment_from_visual(visual_asset, equipment)
    visual_text = _visual_text(visual_asset)
    component_items = analysis.get("component_candidates") or []
    defect_items = analysis.get("defect_labels") or []
    component_keys = []
    for item in component_items:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("id") or item.get("label") or "")
        canonical = canonical_component_key(equipment_id, raw).split(".", 1)[-1]
        if canonical and canonical != "unknown" and canonical not in component_keys:
            component_keys.append(canonical)
    for key in _default_component_ids(equipment_id, visual_text):
        if key not in component_keys:
            component_keys.append(key)

    return {
        "visual_asset_id": visual_asset.get("id"),
        "source_photo_path": visual_asset.get("stored_path", ""),
        "filename": visual_asset.get("filename", ""),
        "equipment": equipment_id,
        "model": model or visual_asset.get("model", ""),
        "caption": analysis.get("caption") or visual_asset.get("caption", ""),
        "ocr_text": analysis.get("ocr_text", ""),
        "component_candidates": component_items,
        "defect_labels": defect_items,
        "component_keys": [f"{equipment_id}.{key}" for key in component_keys],
        "confidence": round(max(_candidate_score(component_items), _candidate_score(defect_items)), 2),
        "geometry_hints": _geometry_hints(equipment_id, visual_text),
        "limits": [
            "single-view observation cannot infer hidden geometry",
            "dimensions are estimated unless OCR/铭牌 provides explicit values",
            "candidate CAD requires human mechanical review before entering the standard asset library",
        ],
    }


def _geometry_hints(equipment: str, text: str) -> dict[str, Any]:
    if equipment == "bearing":
        return {
            "dominant_shape": "coaxial rings",
            "axis": "central rotational axis",
            "features": ["inner bore", "outer ring", "rolling element pitch circle", "optional seal groove"],
            "estimated_primitives": ["torus-like rings", "spheres/cylinders for rolling elements"],
        }
    if equipment == "pump":
        return {
            "dominant_shape": "volute/cylindrical pump body",
            "ports": ["front inlet", "top/side outlet"],
            "features": ["flange bolt holes", "shaft centerline", "mechanical seal zone", "bearing housing"],
            "estimated_primitives": ["cylinders", "rounded casing block", "flange plates", "bolt-hole pattern"],
        }
    if equipment == "motor":
        return {
            "dominant_shape": "horizontal cylinder with shaft",
            "features": ["stator shell", "end shields", "output shaft", "terminal box", "cooling fins"],
            "estimated_primitives": ["main cylinder", "coaxial shaft", "box terminal cover", "fin ribs"],
        }
    if equipment == "engine":
        return {
            "dominant_shape": "cylinder block/head assembly",
            "features": ["cylinder head fins", "spark plug boss", "crankcase", "starter/water pump attachments"],
            "estimated_primitives": ["stacked blocks", "rib fins", "plug cylinder", "crankshaft cover"],
        }
    return {"dominant_shape": "unknown", "features": ["manual review required"], "estimated_primitives": []}


def build_cad_spec(observation: dict[str, Any]) -> dict[str, Any]:
    equipment = observation["equipment"]
    components = []
    for index, canonical in enumerate(observation.get("component_keys") or [], start=1):
        label = component_label(equipment, canonical)
        components.append(
            {
                "component_key": canonical,
                "label": label,
                "role": "candidate_geometry_anchor",
                "priority": index,
                "source": "VLM/OCR observation + equipment template",
            }
        )
    return {
        "schema_version": "candidate-cad-spec-v1",
        "equipment": equipment,
        "model": observation.get("model", ""),
        "component_keys": [item["component_key"] for item in components],
        "components": components,
        "geometry_hints": observation.get("geometry_hints", {}),
        "parameters": _default_parameters(equipment),
        "dimension_policy": {
            "source": "estimated_from_single_view_unless_ocr_explicit",
            "unit": "mm",
            "not_for_measurement": True,
        },
        "generation_targets": ["cadquery_python", "openscad", "svg_preview"],
    }


def _default_parameters(equipment: str) -> dict[str, Any]:
    if equipment == "bearing":
        return {"outer_diameter": 52, "inner_diameter": 25, "width": 15, "ball_count": 8}
    if equipment == "pump":
        return {"body_length": 150, "body_height": 96, "port_diameter": 48, "bolt_count": 4, "shaft_diameter": 18}
    if equipment == "motor":
        return {"body_length": 180, "body_diameter": 92, "shaft_diameter": 18, "terminal_box_size": [42, 32, 28]}
    if equipment == "engine":
        return {"block_width": 120, "block_height": 130, "fin_count": 7, "spark_plug_diameter": 14}
    return {"body_length": 100, "body_height": 60}


def _cadquery_code(spec: dict[str, Any]) -> str:
    equipment = spec["equipment"]
    params = spec["parameters"]
    header = [
        "# Candidate CAD generated from Tri-MRO photo observation.",
        "# Review required: this is not a measurement-grade or manufacturing model.",
        "import cadquery as cq",
        "",
    ]
    if equipment == "bearing":
        return "\n".join(
            header
            + [
                f"outer_diameter = {params['outer_diameter']}",
                f"inner_diameter = {params['inner_diameter']}",
                f"width = {params['width']}",
                "outer_ring = cq.Workplane('XY').circle(outer_diameter / 2).circle(inner_diameter / 2).extrude(width)",
                "rolling_path = cq.Workplane('XY').circle((outer_diameter + inner_diameter) / 4).extrude(width * 0.12)",
                "result = outer_ring.union(rolling_path)",
                "show_object(result)",
            ]
        )
    if equipment == "pump":
        return "\n".join(
            header
            + [
                f"body_length = {params['body_length']}",
                f"body_height = {params['body_height']}",
                f"port_diameter = {params['port_diameter']}",
                "casing = cq.Workplane('XY').box(body_length, body_height, body_height * 0.62).edges('|Z').fillet(12)",
                "inlet = cq.Workplane('YZ').circle(port_diameter / 2).extrude(body_length * 0.35)",
                "outlet = cq.Workplane('XZ').workplane(offset=body_height / 2).circle(port_diameter / 2).extrude(body_height * 0.5)",
                "seal_zone = cq.Workplane('XY').circle(28).circle(12).extrude(14)",
                "result = casing.union(inlet).union(outlet).union(seal_zone)",
                "show_object(result)",
            ]
        )
    if equipment == "motor":
        return "\n".join(
            header
            + [
                f"body_length = {params['body_length']}",
                f"body_diameter = {params['body_diameter']}",
                f"shaft_diameter = {params['shaft_diameter']}",
                "body = cq.Workplane('YZ').circle(body_diameter / 2).extrude(body_length)",
                "shaft = cq.Workplane('YZ').circle(shaft_diameter / 2).extrude(body_length * 1.25)",
                "terminal = cq.Workplane('XY').box(42, 32, 28).translate((body_length * 0.15, 0, body_diameter / 2 + 14))",
                "result = body.union(shaft).union(terminal)",
                "show_object(result)",
            ]
        )
    return "\n".join(
        header
        + [
            f"block_width = {params.get('block_width', 120)}",
            f"block_height = {params.get('block_height', 130)}",
            "block = cq.Workplane('XY').box(block_width, 70, block_height).edges('|Z').fillet(4)",
            "spark_plug = cq.Workplane('XY').circle(7).extrude(36).translate((0, 0, block_height / 2))",
            "result = block.union(spark_plug)",
            "show_object(result)",
        ]
    )


def _openscad_code(spec: dict[str, Any]) -> str:
    equipment = spec["equipment"]
    p = spec["parameters"]
    header = "// Candidate CAD generated by Tri-MRO. Human review required.\n$fn = 72;\n"
    if equipment == "bearing":
        return (
            header
            + f"difference() {{ cylinder(h={p['width']}, d={p['outer_diameter']}); cylinder(h={p['width'] + 1}, d={p['inner_diameter']}); }}\n"
            + f"for (i=[0:{p['ball_count'] - 1}]) rotate([0,0,i*360/{p['ball_count']}]) translate([{(p['outer_diameter'] + p['inner_diameter']) / 4},0,{p['width']/2}]) sphere(d=6);\n"
        )
    if equipment == "pump":
        return (
            header
            + f"cube([{p['body_length']},{p['body_height']},{p['body_height'] * 0.62}], center=true);\n"
            + f"rotate([0,90,0]) cylinder(h={p['body_length'] * 1.2}, d={p['port_diameter']}, center=true);\n"
            + f"translate([0,0,{p['body_height']/2}]) cylinder(h={p['body_height'] * 0.5}, d={p['port_diameter']}, center=false);\n"
            + "color(\"orange\") cylinder(h=18, d=56, center=true);\n"
        )
    if equipment == "motor":
        return (
            header
            + f"rotate([0,90,0]) cylinder(h={p['body_length']}, d={p['body_diameter']}, center=true);\n"
            + f"rotate([0,90,0]) cylinder(h={p['body_length'] * 1.25}, d={p['shaft_diameter']}, center=true);\n"
            + "translate([0,0,60]) cube([48,34,28], center=true);\n"
        )
    return (
        header
        + f"cube([{p.get('block_width', 120)},70,{p.get('block_height', 130)}], center=true);\n"
        + f"translate([0,0,{p.get('block_height', 130)/2}]) cylinder(h=36, d={p.get('spark_plug_diameter', 14)}, center=false);\n"
    )


def _svg_preview(spec: dict[str, Any]) -> str:
    equipment = spec["equipment"]
    title = f"Candidate CAD preview: {equipment}"
    if equipment == "pump":
        body = """
        <rect x="88" y="92" width="210" height="128" rx="34" fill="#d9ebe8" stroke="#1d6f65" stroke-width="5"/>
        <circle cx="116" cy="156" r="48" fill="#f6fbfa" stroke="#1d6f65" stroke-width="5"/>
        <rect x="256" y="126" width="94" height="60" rx="12" fill="#eef6f4" stroke="#1d6f65" stroke-width="4"/>
        <rect x="184" y="38" width="58" height="78" rx="12" fill="#e7f2ef" stroke="#1d6f65" stroke-width="4"/>
        <circle cx="198" cy="156" r="28" fill="#f5b456" stroke="#8a5a14" stroke-width="4"/>
        <line x1="198" y1="156" x2="338" y2="156" stroke="#334155" stroke-width="8" stroke-linecap="round"/>
        """
    elif equipment == "motor":
        body = """
        <rect x="86" y="106" width="230" height="112" rx="56" fill="#dbe8f4" stroke="#355c7d" stroke-width="5"/>
        <circle cx="96" cy="162" r="58" fill="none" stroke="#355c7d" stroke-width="5"/>
        <circle cx="306" cy="162" r="58" fill="none" stroke="#355c7d" stroke-width="5"/>
        <line x1="44" y1="162" x2="356" y2="162" stroke="#23364a" stroke-width="10" stroke-linecap="round"/>
        <rect x="170" y="56" width="72" height="48" rx="8" fill="#edf5f8" stroke="#355c7d" stroke-width="4"/>
        """
    elif equipment == "engine":
        body = """
        <rect x="118" y="112" width="164" height="128" rx="14" fill="#e8e0d5" stroke="#6f5842" stroke-width="5"/>
        <g stroke="#6f5842" stroke-width="5"> <line x1="104" y1="126" x2="296" y2="126"/><line x1="104" y1="146" x2="296" y2="146"/><line x1="104" y1="166" x2="296" y2="166"/><line x1="104" y1="186" x2="296" y2="186"/></g>
        <rect x="180" y="62" width="40" height="64" rx="10" fill="#f7f3ec" stroke="#6f5842" stroke-width="4"/>
        <circle cx="200" cy="204" r="38" fill="#f7f3ec" stroke="#6f5842" stroke-width="5"/>
        """
    else:
        body = """
        <circle cx="200" cy="160" r="86" fill="#edf4f2" stroke="#1d6f65" stroke-width="6"/>
        <circle cx="200" cy="160" r="42" fill="#ffffff" stroke="#1d6f65" stroke-width="5"/>
        <g fill="#f5b456" stroke="#8a5a14" stroke-width="3">
          <circle cx="200" cy="82" r="10"/><circle cx="258" cy="103" r="10"/><circle cx="278" cy="160" r="10"/><circle cx="258" cy="218" r="10"/>
          <circle cx="200" cy="238" r="10"/><circle cx="142" cy="218" r="10"/><circle cx="122" cy="160" r="10"/><circle cx="142" cy="103" r="10"/>
        </g>
        """
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="320" viewBox="0 0 400 320" role="img" aria-label="{title}">
  <rect width="400" height="320" fill="#f7faf9"/>
  <text x="24" y="30" fill="#102233" font-family="Arial" font-size="18" font-weight="700">{title}</text>
  {body}
  <text x="24" y="294" fill="#637285" font-family="Arial" font-size="12">Not for measurement. Human review required.</text>
</svg>
"""


def _render_report(spec: dict[str, Any], artifact_paths: dict[str, str]) -> dict[str, Any]:
    return {
        "renderer": "deterministic_svg_preview",
        "status": "rendered",
        "views": ["front", "side", "isometric_stub"],
        "artifacts": artifact_paths,
        "limitations": [
            "SVG preview is a deterministic proxy for v1",
            "CadQuery/OpenSCAD files are generated for later execution in a CAD sandbox",
        ],
    }


def _vlm_compare(observation: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    observed = set(observation.get("component_keys") or [])
    specified = set(spec.get("component_keys") or [])
    overlap = len(observed & specified)
    denominator = max(1, len(observed))
    score = round(min(0.95, 0.35 + 0.55 * overlap / denominator + 0.1 * float(observation.get("confidence") or 0)), 2)
    status = "pass" if score >= 0.78 else "needs_review" if score >= 0.55 else "reject"
    return {
        "provider": "cached_vlm_compare_v1",
        "status": status,
        "similarity_score": score,
        "matched_component_keys": sorted(observed & specified),
        "missing_component_keys": sorted(observed - specified),
        "review_notes": "VLM comparison is a cached deterministic proxy in v1; final judgement requires mechanical review.",
    }


def _risk_boundary() -> dict[str, Any]:
    return risk_boundary()


def _manifest_file(path: Path) -> dict[str, Any]:
    return file_item(path, project_root=PROJECT_ROOT)


def _artifact_dir_for(candidate_id: int, equipment: str) -> Path:
    return CANDIDATE_ROOT / f"candidate_{candidate_id:04d}_{_safe_slug(equipment)}"


def _write_candidate_artifacts(
    *,
    artifact_dir: Path,
    observation: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    cadquery_path = artifact_dir / "candidate_model.py"
    openscad_path = artifact_dir / "candidate_model.scad"
    preview_path = artifact_dir / "preview.svg"
    spec_path = artifact_dir / "cad_spec.json"
    observation_path = artifact_dir / "observation.json"
    render_report_path = artifact_dir / "render_report.json"
    compare_path = artifact_dir / "comparison_report.json"
    manifest_path = artifact_dir / "artifact_manifest.json"
    runtime_path = artifact_dir / "runtime_report.json"

    cadquery_path.write_text(cadquery_code(spec), encoding="utf-8")
    openscad_path.write_text(openscad_code(spec), encoding="utf-8")
    preview_path.write_text(_svg_preview(spec), encoding="utf-8")
    spec_path.write_text(_json_dumps(spec), encoding="utf-8")
    observation_path.write_text(_json_dumps(observation), encoding="utf-8")

    rendered = render_candidate_artifacts(artifact_dir, spec=spec, project_root=PROJECT_ROOT)
    artifact_manifest = rendered["artifact_manifest"]
    artifact_manifest["source_files"]["cadquery"] = _manifest_file(cadquery_path)
    artifact_manifest["source_files"]["openscad"] = _manifest_file(openscad_path)
    artifact_manifest["source_files"]["cad_spec"] = _manifest_file(spec_path)
    artifact_manifest["source_files"]["observation"] = _manifest_file(observation_path)
    artifact_manifest["legacy_preview"] = _manifest_file(preview_path)
    runtime_report = rendered["runtime_report"]
    comparison_report = compare_candidate_to_observation(observation, spec, artifact_manifest)
    render_report = {
        "renderer": runtime_report.get("recommended_mode", "python_render"),
        "status": "rendered",
        "views": list((artifact_manifest.get("renders") or {}).keys()),
        "artifacts": artifact_manifest,
        "limitations": [
            "Candidate CAD is not measurement-grade.",
            "Mechanical review is required before structure-chain promotion.",
        ],
    }
    render_artifacts = {
        "preview_svg": _relative_path(preview_path),
        "front_png": (artifact_manifest.get("renders", {}).get("front") or {}).get("path", ""),
        "side_png": (artifact_manifest.get("renders", {}).get("side") or {}).get("path", ""),
        "top_png": (artifact_manifest.get("renders", {}).get("top") or {}).get("path", ""),
        "iso_png": (artifact_manifest.get("renders", {}).get("iso") or {}).get("path", ""),
        "glb": (artifact_manifest.get("cad_files", {}).get("glb") or {}).get("path", ""),
    }
    code_artifacts = {
        "cadquery": _relative_path(cadquery_path),
        "openscad": _relative_path(openscad_path),
        "cad_spec": _relative_path(spec_path),
        "observation": _relative_path(observation_path),
    }
    manifest_path.write_text(_json_dumps(artifact_manifest), encoding="utf-8")
    runtime_path.write_text(_json_dumps(runtime_report), encoding="utf-8")
    render_report_path.write_text(_json_dumps(render_report), encoding="utf-8")
    compare_path.write_text(_json_dumps(comparison_report), encoding="utf-8")
    return {
        "code_artifacts": code_artifacts,
        "render_artifacts": render_artifacts,
        "render_report": render_report,
        "comparison_report": comparison_report,
        "runtime_report": runtime_report,
        "artifact_manifest": artifact_manifest,
    }


def create_candidate_from_visual_asset(
    conn: sqlite3.Connection,
    visual_asset: dict[str, Any],
    *,
    equipment: str = "",
    model: str = "",
    generator: str = "cadquery_openscad",
) -> dict[str, Any]:
    observation = build_cad_observation(visual_asset, equipment=equipment, model=model)
    spec = build_cad_spec(observation)
    now = _utc()
    cursor = conn.execute(
        """
        INSERT INTO candidate_cad_assets
        (visual_asset_id, equipment, model, source_photo_path, generator, status,
         observation_json, cad_spec_json, editable_spec_json, risk_boundary_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'needs_review', ?, ?, ?, ?, ?, ?)
        """,
        (
            visual_asset.get("id"),
            observation["equipment"],
            observation.get("model", ""),
            observation.get("source_photo_path", ""),
            generator or "cadquery_openscad",
            _json_dumps(observation),
            _json_dumps(spec),
            _json_dumps(spec),
            _json_dumps(_risk_boundary()),
            now,
            now,
        ),
    )
    candidate_id = int(cursor.lastrowid)
    conn.commit()

    artifact_dir = _artifact_dir_for(candidate_id, observation["equipment"])
    artifacts = _write_candidate_artifacts(artifact_dir=artifact_dir, observation=observation, spec=spec)
    vlm_compare = artifacts["comparison_report"]

    conn.execute(
        """
        UPDATE candidate_cad_assets
        SET code_artifacts_json = ?, render_artifacts_json = ?, render_report_json = ?,
            vlm_compare_json = ?, comparison_report_json = ?, artifact_manifest_json = ?,
            runtime_report_json = ?, artifact_dir = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            _json_dumps(artifacts["code_artifacts"]),
            _json_dumps(artifacts["render_artifacts"]),
            _json_dumps(artifacts["render_report"]),
            _json_dumps(vlm_compare),
            _json_dumps(artifacts["comparison_report"]),
            _json_dumps(artifacts["artifact_manifest"]),
            _json_dumps(artifacts["runtime_report"]),
            _relative_path(artifact_dir),
            _utc(),
            candidate_id,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM candidate_cad_assets WHERE id = ?", (candidate_id,)).fetchone()
    return row_to_candidate(row)


def _relative_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def row_to_candidate(row: sqlite3.Row) -> dict[str, Any]:
    candidate = dict(row)
    candidate["observation"] = _json_loads(candidate.pop("observation_json", ""), {})
    candidate["cad_spec"] = _json_loads(candidate.pop("cad_spec_json", ""), {})
    candidate["editable_spec"] = _json_loads(candidate.pop("editable_spec_json", ""), candidate["cad_spec"])
    candidate["code_artifacts"] = _json_loads(candidate.pop("code_artifacts_json", ""), {})
    candidate["render_artifacts"] = _json_loads(candidate.pop("render_artifacts_json", ""), {})
    candidate["render_report"] = _json_loads(candidate.pop("render_report_json", ""), {})
    candidate["vlm_compare"] = _json_loads(candidate.pop("vlm_compare_json", ""), {})
    candidate["comparison_report"] = _json_loads(candidate.pop("comparison_report_json", ""), candidate["vlm_compare"])
    candidate["artifact_manifest"] = _json_loads(candidate.pop("artifact_manifest_json", ""), build_empty_artifact_manifest())
    candidate["runtime_report"] = _json_loads(candidate.pop("runtime_report_json", ""), {})
    candidate["promotion"] = _json_loads(candidate.pop("promotion_json", ""), {})
    candidate["risk_boundary"] = _json_loads(candidate.pop("risk_boundary_json", ""), _risk_boundary())
    candidate["review_gate"] = {
        "required": candidate["status"] not in {"approved_candidate", "promoted_standard_asset"},
        "allowed_statuses": sorted(ALLOWED_REVIEW_STATUSES),
        "promotion_rule": "approved_candidate may be manually promoted to standard CAD after license and geometry review",
    }
    return candidate


def list_candidate_assets(conn: sqlite3.Connection, *, status: str = "", limit: int = 40) -> dict[str, Any]:
    safe_limit = min(max(int(limit or 40), 1), 200)
    if status:
        rows = conn.execute(
            "SELECT * FROM candidate_cad_assets WHERE status = ? ORDER BY id DESC LIMIT ?",
            (status, safe_limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM candidate_cad_assets ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    summary_rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM candidate_cad_assets GROUP BY status"
    ).fetchall()
    summary = {row["status"]: row["count"] for row in summary_rows}
    summary["total"] = sum(summary.values())
    return {"summary": summary, "candidates": [row_to_candidate(row) for row in rows]}


def get_candidate_asset(conn: sqlite3.Connection, candidate_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM candidate_cad_assets WHERE id = ?", (candidate_id,)).fetchone()
    return row_to_candidate(row) if row else None


def patch_candidate_spec(
    conn: sqlite3.Connection,
    candidate_id: int,
    *,
    parameters: dict[str, Any] | None = None,
    component_keys: list[str] | None = None,
    review_notes: str = "",
) -> dict[str, Any]:
    candidate = get_candidate_asset(conn, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    editable = dict(candidate.get("editable_spec") or candidate.get("cad_spec") or {})
    editable_parameters = dict(editable.get("parameters") or {})
    editable_parameters.update(parameters or {})
    editable["parameters"] = editable_parameters
    if component_keys:
        editable["component_keys"] = component_keys
        component_entries = editable.get("components") or []
        existing_by_key = {item.get("component_key"): item for item in component_entries if isinstance(item, dict)}
        editable["components"] = [
            existing_by_key.get(key, {"component_key": key, "label": key.split(".")[-1], "role": "manual_review_anchor", "source": "manual_patch"})
            for key in component_keys
        ]
    conn.execute(
        """
        UPDATE candidate_cad_assets
        SET editable_spec_json = ?, review_notes = ?, status = 'needs_review', updated_at = ?
        WHERE id = ?
        """,
        (
            _json_dumps(editable),
            review_notes or candidate.get("review_notes", ""),
            _utc(),
            candidate_id,
        ),
    )
    conn.commit()
    updated = get_candidate_asset(conn, candidate_id)
    if not updated:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    return updated


def regenerate_candidate_artifacts(conn: sqlite3.Connection, candidate_id: int) -> dict[str, Any]:
    candidate = get_candidate_asset(conn, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    spec = candidate.get("editable_spec") or candidate.get("cad_spec") or {}
    observation = candidate.get("observation") or {}
    artifact_dir = PROJECT_ROOT / (candidate.get("artifact_dir") or _relative_path(_artifact_dir_for(candidate_id, candidate.get("equipment", "cad"))))
    artifacts = _write_candidate_artifacts(artifact_dir=artifact_dir, observation=observation, spec=spec)
    conn.execute(
        """
        UPDATE candidate_cad_assets
        SET code_artifacts_json = ?, render_artifacts_json = ?, render_report_json = ?,
            vlm_compare_json = ?, comparison_report_json = ?, artifact_manifest_json = ?,
            runtime_report_json = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            _json_dumps(artifacts["code_artifacts"]),
            _json_dumps(artifacts["render_artifacts"]),
            _json_dumps(artifacts["render_report"]),
            _json_dumps(artifacts["comparison_report"]),
            _json_dumps(artifacts["comparison_report"]),
            _json_dumps(artifacts["artifact_manifest"]),
            _json_dumps(artifacts["runtime_report"]),
            _utc(),
            candidate_id,
        ),
    )
    conn.commit()
    updated = get_candidate_asset(conn, candidate_id)
    if not updated:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    return updated


def save_candidate_promotion(conn: sqlite3.Connection, candidate_id: int, promotion: dict[str, Any]) -> dict[str, Any]:
    conn.execute(
        """
        UPDATE candidate_cad_assets
        SET status = 'promoted_standard_asset', promotion_json = ?, updated_at = ?
        WHERE id = ?
        """,
        (_json_dumps(promotion), _utc(), candidate_id),
    )
    conn.commit()
    updated = get_candidate_asset(conn, candidate_id)
    if not updated:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    return updated


def review_candidate_asset(
    conn: sqlite3.Connection,
    candidate_id: int,
    *,
    status: str,
    reviewer: str = "",
    notes: str = "",
) -> dict[str, Any]:
    if status not in ALLOWED_REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail=f"unsupported candidate CAD status: {status}")
    row = conn.execute("SELECT id FROM candidate_cad_assets WHERE id = ?", (candidate_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    approved_at = _utc() if status in {"approved_candidate", "promoted_standard_asset"} else ""
    conn.execute(
        """
        UPDATE candidate_cad_assets
        SET status = ?, reviewer = ?, review_notes = ?, approved_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, reviewer, notes, approved_at, _utc(), candidate_id),
    )
    conn.commit()
    candidate = get_candidate_asset(conn, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    return candidate


def resolve_candidate_file(conn: sqlite3.Connection, candidate_id: int, file_role: str) -> Path:
    candidate = get_candidate_asset(conn, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    manifest = candidate.get("artifact_manifest") or {}
    cad_files = manifest.get("cad_files") or {}
    renders = manifest.get("renders") or {}
    role_to_path = {
        "cadquery": candidate.get("code_artifacts", {}).get("cadquery", ""),
        "openscad": candidate.get("code_artifacts", {}).get("openscad", ""),
        "spec": candidate.get("code_artifacts", {}).get("cad_spec", ""),
        "observation": candidate.get("code_artifacts", {}).get("observation", ""),
        "preview": candidate.get("render_artifacts", {}).get("preview_svg", ""),
        "step": (cad_files.get("step") or {}).get("path", ""),
        "stl": (cad_files.get("stl") or {}).get("path", ""),
        "openscad-stl": (cad_files.get("openscad_stl") or {}).get("path", ""),
        "glb": (cad_files.get("glb") or {}).get("path", ""),
        "fcstd": (cad_files.get("fcstd") or {}).get("path", ""),
        "render-front": (renders.get("front") or {}).get("path", ""),
        "render-side": (renders.get("side") or {}).get("path", ""),
        "render-top": (renders.get("top") or {}).get("path", ""),
        "render-iso": (renders.get("iso") or {}).get("path", ""),
        "comparison": f"{candidate.get('artifact_dir', '')}/comparison_report.json" if candidate.get("artifact_dir") else "",
        "artifact-manifest": f"{candidate.get('artifact_dir', '')}/artifact_manifest.json" if candidate.get("artifact_dir") else "",
        "runtime": f"{candidate.get('artifact_dir', '')}/runtime_report.json" if candidate.get("artifact_dir") else "",
        "freecad-validation": f"{candidate.get('artifact_dir', '')}/freecad_validation.json" if candidate.get("artifact_dir") else "",
        "blender-report": f"{candidate.get('artifact_dir', '')}/blender_render_report.json" if candidate.get("artifact_dir") else "",
        "openscad-report": f"{candidate.get('artifact_dir', '')}/openscad_export_report.json" if candidate.get("artifact_dir") else "",
    }
    relative_path = role_to_path.get(file_role)
    if not relative_path:
        raise HTTPException(status_code=404, detail="candidate CAD file role not found")
    target = (PROJECT_ROOT / relative_path).resolve()
    allowed_root = CANDIDATE_ROOT.resolve()
    if not (target == allowed_root or allowed_root in target.parents):
        raise HTTPException(status_code=403, detail="candidate CAD file outside allowed root")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="candidate CAD file not found")
    return target
