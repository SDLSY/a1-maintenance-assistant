from __future__ import annotations

import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "3d" / "authorized_models" / "manifest.json"
REPORT = ROOT / "data" / "3d" / "authorized_models" / "verification_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_glb(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("GLB file is too small")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError("GLB magic is not glTF")
    if version != 2:
        raise ValueError(f"Unsupported GLB version: {version}")
    if declared_length != len(data):
        raise ValueError(f"GLB declared length {declared_length} != actual {len(data)}")
    json_length, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise ValueError("First GLB chunk is not JSON")
    json_start = 20
    json_end = json_start + json_length
    payload = json.loads(data[json_start:json_end].decode("utf-8").rstrip(" \t\r\n\0"))
    return {
        "version": version,
        "bytes": len(data),
        "nodes": len(payload.get("nodes", [])),
        "meshes": len(payload.get("meshes", [])),
        "materials": len(payload.get("materials", [])),
        "node_names": [node.get("name", "") for node in payload.get("nodes", [])],
    }


def verify_resource(resource: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    root = MANIFEST.parent

    sidecar_path = root / resource.get("sidecar", "")
    if not sidecar_path.exists():
        errors.append(f"missing sidecar: {sidecar_path}")
        sidecar: dict[str, Any] = {}
    else:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))

    checked_files = []
    for key in ("primary_file", "native_file"):
        rel = resource.get(key, "")
        path = root / rel
        if not path.exists():
            errors.append(f"missing {key}: {rel}")
            continue
        checked_files.append({"role": key, "path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})

    mesh_rel = resource.get("processed_mesh_path") or sidecar.get("processed_mesh", {}).get("path", "")
    glb_info = None
    if mesh_rel:
        mesh_path = ROOT / mesh_rel
        if not mesh_path.exists():
            errors.append(f"missing processed GLB: {mesh_rel}")
        else:
            try:
                glb_info = parse_glb(mesh_path)
                if glb_info["meshes"] < 1:
                    errors.append("processed GLB has no mesh")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"invalid GLB: {exc}")
    else:
        warnings.append("no processed_mesh_path yet")

    semantics = sidecar.get("part_semantics", [])
    if len(semantics) < 5:
        errors.append("sidecar must contain at least 5 part semantics")

    bindings = sidecar.get("node_bindings", {})
    if resource.get("viewer_mode") == "local_glb":
        if bindings.get("binding_mode") != "named_glb_node_with_semantic_hotspots":
            warnings.append("local GLB does not declare named object marker binding mode")
        cad_mesh = resource.get("node_bindings", {}).get("cad_mesh") or bindings.get("cad_mesh", "")
        if glb_info and cad_mesh and cad_mesh not in glb_info["node_names"]:
            errors.append(f"cad mesh node not found in GLB: {cad_mesh}")
        marker_nodes = [
            binding.get("node")
            for key, binding in bindings.items()
            if key not in {"cad_mesh", "binding_mode", "exact_cad_face_binding", "object_level_binding"}
            and isinstance(binding, dict)
            and binding.get("node")
        ]
        missing_marker_nodes = [node for node in marker_nodes if glb_info and node not in glb_info["node_names"]]
        if missing_marker_nodes:
            errors.append(f"bound component marker nodes missing from GLB: {missing_marker_nodes}")

    if resource.get("verify_status") != "passed":
        errors.append("resource verify_status is not passed")
    if not resource.get("license") or not resource.get("license_url"):
        errors.append("missing license metadata")

    return {
        "id": resource.get("id"),
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "license": resource.get("license"),
        "checked_files": checked_files,
        "sidecar_semantics": len(semantics),
        "glb": glb_info,
    }


def verify() -> dict[str, Any]:
    if not MANIFEST.exists():
        raise SystemExit(f"Missing authorized 3D manifest: {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    resources = [verify_resource(resource) for resource in manifest.get("resources", [])]
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "overall_status": "passed" if resources and all(item["status"] == "passed" for item in resources) else "failed",
        "resources": resources,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    report = verify()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
