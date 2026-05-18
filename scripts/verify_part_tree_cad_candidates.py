from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "3d" / "part_tree_candidates" / "candidate_manifest.json"
REPORT_PATH = ROOT / "data" / "3d" / "part_tree_candidates" / "verification_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing candidate manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, *, limit_mb: int = 120) -> str:
    if path.stat().st_size > limit_mb * 1024 * 1024:
        raise ValueError(f"file exceeds {limit_mb}MB verification limit")
    return path.read_text(encoding="utf-8", errors="replace")


def unescape_step_name(value: str) -> str:
    return value.replace("''", "'").strip()


def analyze_step(path: Path) -> dict[str, Any]:
    data = path.read_bytes()[:64]
    if not data.startswith(b"ISO-10303-21"):
        return {
            "format": "not_step",
            "cad_readable": False,
            "errors": ["STEP file does not start with ISO-10303-21"],
        }

    text = read_text(path)
    product_names = [
        unescape_step_name(match.group(1))
        for match in re.finditer(r"=\s*PRODUCT\s*\(\s*'((?:''|[^'])*)'", text, flags=re.IGNORECASE)
    ]
    product_names = [name for name in product_names if name and name not in {" ", "$"}]
    unique_product_names = list(dict.fromkeys(product_names))
    product_count = len(product_names)
    next_assembly_usage_count = len(re.findall(r"NEXT_ASSEMBLY_USAGE_OCCURRENCE", text, flags=re.IGNORECASE))
    manifold_solid_count = len(re.findall(r"MANIFOLD_SOLID_BREP", text, flags=re.IGNORECASE))
    brep_with_voids_count = len(re.findall(r"BREP_WITH_VOIDS", text, flags=re.IGNORECASE))
    solid_count = manifold_solid_count + brep_with_voids_count
    advanced_brep_shape_representation_count = len(
        re.findall(r"ADVANCED_BREP_SHAPE_REPRESENTATION", text, flags=re.IGNORECASE)
    )
    mapped_item_count = len(re.findall(r"MAPPED_ITEM", text, flags=re.IGNORECASE))
    file_schema = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", text, flags=re.IGNORECASE)

    if next_assembly_usage_count > 0 or product_count >= 4:
        classification = "assembly_tree"
    elif solid_count >= 2 or advanced_brep_shape_representation_count >= 2:
        classification = "multi_solid_cad"
    elif solid_count == 1:
        classification = "single_body_cad"
    else:
        classification = "cad_unclassified"

    return {
        "format": "step",
        "cad_readable": True,
        "classification": classification,
        "file_schema": file_schema.group(1) if file_schema else "",
        "product_count": product_count,
        "unique_product_name_count": len(unique_product_names),
        "sample_product_names": unique_product_names[:30],
        "next_assembly_usage_count": next_assembly_usage_count,
        "mapped_item_count": mapped_item_count,
        "solid_count": solid_count,
        "manifold_solid_brep_count": manifold_solid_count,
        "brep_with_voids_count": brep_with_voids_count,
        "advanced_brep_shape_representation_count": advanced_brep_shape_representation_count,
        "errors": [],
    }


def analyze_fcstd(path: Path) -> dict[str, Any]:
    if not zipfile.is_zipfile(path):
        return {
            "format": "not_fcstd",
            "cad_readable": False,
            "errors": ["FCStd file is not a valid zip container"],
        }
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if "Document.xml" not in names:
            return {
                "format": "fcstd",
                "cad_readable": False,
                "errors": ["FCStd archive does not contain Document.xml"],
            }
        document = archive.read("Document.xml").decode("utf-8", errors="replace")
        gui_document = archive.read("GuiDocument.xml").decode("utf-8", errors="replace") if "GuiDocument.xml" in names else ""

    object_names = re.findall(r"<Object\b[^>]*\bname=\"([^\"]+)\"", document)
    object_types = re.findall(r"<Object\b[^>]*\btype=\"([^\"]+)\"", document)
    mesh_count = sum(1 for item in object_types if "Mesh::" in item)
    part_count = sum(1 for item in object_types if item.startswith("Part::") or "PartDesign::" in item)
    feature_count = len(object_types)
    visible_object_refs = re.findall(r"<ViewProvider\b[^>]*\bname=\"([^\"]+)\"", gui_document)

    if feature_count >= 8 and part_count >= 2:
        classification = "freecad_feature_tree"
    elif feature_count >= 3:
        classification = "freecad_parametric_or_multi_object"
    elif feature_count == 1:
        classification = "freecad_single_object"
    else:
        classification = "freecad_unclassified"

    return {
        "format": "fcstd",
        "cad_readable": True,
        "classification": classification,
        "object_count": len(object_names),
        "feature_count": feature_count,
        "part_like_object_count": part_count,
        "mesh_object_count": mesh_count,
        "visible_object_count": len(visible_object_refs),
        "sample_object_names": object_names[:30],
        "sample_object_types": list(dict.fromkeys(object_types))[:30],
        "errors": [],
    }


def verify_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    local_path = ROOT / candidate["local_path"]
    item: dict[str, Any] = {
        "id": candidate["id"],
        "equipment": candidate["equipment"],
        "title": candidate["title"],
        "local_path": rel(local_path) if local_path.exists() else candidate["local_path"],
        "source_url": candidate.get("source_url", ""),
        "license": candidate.get("license", ""),
        "intended_use": candidate.get("intended_use", ""),
        "status": "failed",
        "errors": [],
        "warnings": [],
    }
    if not local_path.exists():
        item["errors"].append("local file is missing")
        return item

    item.update(
        {
            "bytes": local_path.stat().st_size,
            "sha256": sha256(local_path),
            "suffix": local_path.suffix.lower(),
        }
    )
    try:
        if local_path.suffix.lower() in {".step", ".stp"}:
            analysis = analyze_step(local_path)
        elif local_path.suffix.lower() in {".fcstd"}:
            analysis = analyze_fcstd(local_path)
        else:
            analysis = {
                "format": "unsupported",
                "cad_readable": False,
                "errors": [f"unsupported CAD suffix: {local_path.suffix}"],
            }
    except Exception as exc:  # noqa: BLE001 - report verification failures as data
        analysis = {
            "format": "unknown",
            "cad_readable": False,
            "errors": [repr(exc)],
        }

    item["analysis"] = analysis
    item["errors"].extend(analysis.get("errors", []))
    classification = analysis.get("classification", "")
    accepted_classes = set(candidate.get("accepted_classifications", []))
    if analysis.get("format") == "step" and analysis.get("cad_readable"):
        if analysis.get("next_assembly_usage_count", 0) == 0 and analysis.get("product_count", 0) <= 1:
            item["warnings"].append(
                "STEP contains multiple solids but no explicit product assembly tree; manual object naming will be required"
            )
        advertised_solids = candidate.get("advertised_solids")
        if advertised_solids and analysis.get("solid_count") and int(advertised_solids) != int(analysis["solid_count"]):
            item["warnings"].append(
                f"source advertised {advertised_solids} solids; parser counted {analysis['solid_count']} solid B-reps"
            )
    if not analysis.get("cad_readable"):
        item["status"] = "failed"
    elif accepted_classes and classification not in accepted_classes:
        item["status"] = "blocked"
        item["warnings"].append(f"classification {classification!r} is below intended part-tree target")
    else:
        item["status"] = "passed"
    return item


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify downloaded CAD candidates for assembly or multi-solid structure.")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--output", default=str(REPORT_PATH))
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    report_path = Path(args.output)
    manifest = read_manifest(manifest_path)
    candidates = manifest.get("candidates", [])
    results = [verify_candidate(candidate) for candidate in candidates]
    summary = {
        "total": len(results),
        "passed": sum(1 for item in results if item["status"] == "passed"),
        "blocked": sum(1 for item in results if item["status"] == "blocked"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "assembly_tree": sum(1 for item in results if item.get("analysis", {}).get("classification") == "assembly_tree"),
        "multi_solid_or_feature_tree": sum(
            1
            for item in results
            if item.get("analysis", {}).get("classification")
            in {"multi_solid_cad", "freecad_feature_tree", "freecad_parametric_or_multi_object"}
        ),
    }
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manifest_path": rel(manifest_path.resolve()),
        "summary": summary,
        "results": results,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"summary": summary, "report": rel(report_path.resolve())}, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
