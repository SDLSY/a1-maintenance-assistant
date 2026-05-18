from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "3d" / "authorized_models" / "manifest.json"
TMP_ROOT = ROOT / "tmp" / "3d_conversion"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_manifest_path(value: str) -> Path:
    return MANIFEST_PATH.parent / value


def resolve_project_path(value: str) -> Path:
    return ROOT / value


def load_manifest() -> list[dict[str, Any]]:
    manifest = read_json(MANIFEST_PATH, {"resources": []})
    return list(manifest.get("resources", []))


def as_mesh(loaded: Any) -> Any:
    import trimesh

    if isinstance(loaded, trimesh.Scene):
        meshes = [geometry for geometry in loaded.geometry.values() if hasattr(geometry, "vertices")]
        if not meshes:
            raise ValueError("source mesh scene contains no mesh geometry")
        return trimesh.util.concatenate(meshes)
    return loaded


def scaled_hotspot(bounds: Any, hotspot: list[float]) -> list[float]:
    lower = bounds[0]
    upper = bounds[1]
    center = (lower + upper) / 2
    extent = upper - lower
    return [float(center[index] + float(hotspot[index]) * extent[index] / 2) for index in range(3)]


def add_annotation_nodes(scene: Any, mesh: Any, sidecar: dict[str, Any], asset_id: str) -> list[str]:
    import trimesh

    bounds = mesh.bounds
    max_extent = float(max(bounds[1] - bounds[0])) or 1.0
    marker_radius = max_extent * 0.012
    node_names: list[str] = []
    bindings = sidecar.get("node_bindings", {})
    if not isinstance(bindings, dict):
        return node_names
    for component in sidecar.get("part_semantics", []):
        key = component.get("id", "")
        binding = bindings.get(key, {})
        if not key or not isinstance(binding, dict):
            continue
        hotspot = binding.get("hotspot", [])
        if len(hotspot) != 3:
            continue
        node_name = binding.get("node") or f"{asset_id}__{key}_marker"
        marker = trimesh.creation.icosphere(subdivisions=2, radius=marker_radius)
        marker.apply_translation(scaled_hotspot(bounds, hotspot))
        scene.add_geometry(marker, node_name=node_name, geom_name=node_name)
        node_names.append(node_name)
    return node_names


def cadquery_step_to_stl(resource: dict[str, Any], source_step: Path, tolerance: float, angular_tolerance: float) -> Path:
    try:
        from cadquery import exporters, importers
    except ImportError as exc:
        raise RuntimeError("cadquery is required when no source STL fallback is available") from exc

    asset_id = resource["id"]
    tmp_dir = TMP_ROOT / asset_id
    tmp_dir.mkdir(parents=True, exist_ok=True)
    stl_path = tmp_dir / f"{Path(resource['primary_file']).stem}.tessellated.stl"
    workplane = importers.importStep(str(source_step))
    exporters.export(
        workplane,
        str(stl_path),
        exportType="STL",
        tolerance=tolerance,
        angularTolerance=angular_tolerance,
    )
    return stl_path


def source_to_stl(
    resource: dict[str, Any],
    source_step: Path,
    *,
    tolerance: float,
    angular_tolerance: float,
    force_step: bool,
) -> tuple[Path, dict[str, Any]]:
    source_stl_rel = resource.get("tessellated_file", "")
    source_stl = resolve_manifest_path(source_stl_rel) if source_stl_rel else None
    if source_stl and source_stl.exists() and not force_step:
        return source_stl, {
            "cad_import": "FreeCAD-library source STL fallback",
            "tessellation": "pre-tessellated STL distributed with the same CC-BY-3.0 source asset",
            "tolerance": None,
            "angular_tolerance": None,
        }
    stl_path = cadquery_step_to_stl(resource, source_step, tolerance, angular_tolerance)
    return stl_path, {
        "cad_import": "cadquery.importers.importStep",
        "tessellation": "cadquery.exporters.export(..., exportType='STL')",
        "tolerance": tolerance,
        "angular_tolerance": angular_tolerance,
    }


def source_to_mesh_path(
    resource: dict[str, Any],
    source_primary: Path,
    *,
    tolerance: float,
    angular_tolerance: float,
    force_step: bool,
) -> tuple[Path, dict[str, Any]]:
    suffix = source_primary.suffix.lower()
    if suffix in {".obj", ".stl", ".ply"}:
        return source_primary, {
            "cad_import": f"source {suffix.upper().lstrip('.')} mesh",
            "tessellation": "source mesh used directly",
            "tolerance": None,
            "angular_tolerance": None,
        }
    return source_to_stl(
        resource,
        source_primary,
        tolerance=tolerance,
        angular_tolerance=angular_tolerance,
        force_step=force_step,
    )


def convert_resource(
    resource: dict[str, Any],
    *,
    tolerance: float = 0.035,
    angular_tolerance: float = 0.08,
    force_step: bool = False,
) -> dict[str, Any]:
    try:
        import trimesh
    except ImportError as exc:
        raise SystemExit("Missing trimesh. Install with: python -m pip install -r requirements-3d.txt") from exc

    asset_id = resource["id"]
    source_primary = resolve_manifest_path(resource.get("primary_file", ""))
    source_native = resolve_manifest_path(resource.get("native_file", ""))
    output_glb = resolve_project_path(resource.get("processed_mesh_path", ""))
    sidecar_path = resolve_manifest_path(resource.get("sidecar", ""))
    report_path = resolve_project_path(
        resource.get("conversion_report", f"data/3d/authorized_models/{asset_id}/conversion_report.json")
    )

    if not source_primary.exists():
        raise SystemExit(f"Missing primary source model: {source_primary}")
    if not source_native.exists():
        raise SystemExit(f"Missing source native CAD: {source_native}")
    if not sidecar_path.exists():
        raise SystemExit(f"Missing sidecar: {sidecar_path}")
    if not output_glb.name:
        raise SystemExit(f"Missing processed_mesh_path for {asset_id}")

    output_glb.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = read_json(sidecar_path, {})

    mesh_path, toolchain = source_to_mesh_path(
        resource,
        source_primary,
        tolerance=tolerance,
        angular_tolerance=angular_tolerance,
        force_step=force_step,
    )
    loaded = trimesh.load(mesh_path, process=True)
    mesh = as_mesh(loaded)

    bindings = sidecar.get("node_bindings", {})
    cad_mesh_node = resource.get("node_bindings", {}).get("cad_mesh") or bindings.get("cad_mesh") or f"{asset_id}_cad_mesh"
    scene = trimesh.Scene()
    scene.add_geometry(mesh, node_name=cad_mesh_node, geom_name=cad_mesh_node)
    annotation_nodes = add_annotation_nodes(scene, mesh, sidecar, asset_id)
    scene.export(output_glb)

    source_files = [
        {
            "path": rel(source_primary),
            "role": "primary_model",
            "bytes": source_primary.stat().st_size,
            "sha256": sha256(source_primary),
        },
        {
            "path": rel(source_native),
            "role": "native_cad",
            "bytes": source_native.stat().st_size,
            "sha256": sha256(source_native),
        },
    ]
    source_stl_rel = resource.get("tessellated_file", "")
    if source_stl_rel:
        source_stl = resolve_manifest_path(source_stl_rel)
        if source_stl.exists():
            source_files.append(
                {
                    "path": rel(source_stl),
                    "role": "source_stl",
                    "bytes": source_stl.stat().st_size,
                    "sha256": sha256(source_stl),
                }
            )

    report = {
        "asset_id": asset_id,
        "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "toolchain": {**toolchain, "glb_packaging": "trimesh.Scene.export"},
        "source_files": source_files,
        "intermediate": {
            "path": rel(mesh_path),
            "bytes": mesh_path.stat().st_size,
            "sha256": sha256(mesh_path),
        },
        "output": {
            "path": rel(output_glb),
            "public_url": resource.get("processed_mesh_url", ""),
            "bytes": output_glb.stat().st_size,
            "sha256": sha256(output_glb),
            "node_names": [cad_mesh_node, *annotation_nodes],
            "cad_mesh_node": cad_mesh_node,
            "annotation_nodes": annotation_nodes,
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
            "bounds": mesh.bounds.tolist(),
        },
        "usage_note": (
            "The GLB is generated from a verified FreeCAD-library asset. Component interaction uses named "
            "annotation nodes plus sidecar semantic hotspots; exact CAD face-level binding is not claimed."
        ),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def select_resources(asset_ids: list[str]) -> list[dict[str, Any]]:
    resources = [resource for resource in load_manifest() if resource.get("viewer_mode") == "local_glb"]
    if not asset_ids:
        return resources
    wanted = set(asset_ids)
    selected = [resource for resource in resources if resource.get("id") in wanted]
    missing = wanted - {resource.get("id") for resource in selected}
    if missing:
        raise SystemExit(f"Unknown asset id(s): {', '.join(sorted(missing))}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert authorized CAD/STL sources to local GLB assets.")
    parser.add_argument("--asset-id", action="append", default=[], help="Convert one asset id; repeatable.")
    parser.add_argument("--tolerance", type=float, default=0.035)
    parser.add_argument("--angular-tolerance", type=float, default=0.08)
    parser.add_argument("--force-step", action="store_true", help="Ignore source STL fallback and tessellate from STEP.")
    args = parser.parse_args()

    reports = [
        convert_resource(
            resource,
            tolerance=args.tolerance,
            angular_tolerance=args.angular_tolerance,
            force_step=args.force_step,
        )
        for resource in select_resources(args.asset_id)
    ]
    print(json.dumps([report["output"] for report in reports], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
