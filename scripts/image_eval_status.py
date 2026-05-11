from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "image_eval" / "fault_image_eval_manifest.csv"
DEFAULT_REPORT = ROOT / "docs" / "IMAGE_EVAL_STATUS.md"
REQUIRED_IMAGES = 30
REQUIRED_EQUIPMENT = {"motor", "pump", "bearing"}
REQUIRED_COLUMNS = {
    "id",
    "image_path",
    "equipment",
    "model",
    "fault_type",
    "visible_evidence",
    "caption_hint",
    "expected_retrieval_keywords",
    "expected_safety_keywords",
    "source_note",
    "license_note",
    "review_status",
    "reviewer",
    "review_notes",
}


def _resolve_image_path(value: str, root: Path = ROOT) -> Path:
    path = Path((value or "").strip())
    if path.is_absolute():
        return path
    return root / path


def _blank_summary(manifest_path: Path, required_images: int) -> dict:
    return {
        "exists": False,
        "manifest": str(manifest_path),
        "required_images": required_images,
        "total": 0,
        "available_images": 0,
        "approved_images": 0,
        "missing_images": 0,
        "invalid_rows": [],
        "missing_columns": sorted(REQUIRED_COLUMNS),
        "by_equipment": {},
        "missing_equipment": sorted(REQUIRED_EQUIPMENT),
        "missing_paths": [],
        "ready": False,
    }


def summarize_manifest(
    manifest_path: Path | str = DEFAULT_MANIFEST,
    *,
    root: Path = ROOT,
    required_images: int = REQUIRED_IMAGES,
) -> dict:
    manifest = Path(manifest_path)
    if not manifest.exists():
        return _blank_summary(manifest, required_images)

    with manifest.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = set(reader.fieldnames or [])

    missing_columns = sorted(REQUIRED_COLUMNS - fieldnames)
    by_equipment: dict[str, dict] = {}
    invalid_rows: list[dict] = []
    missing_paths: list[str] = []
    available = 0
    approved = 0

    for index, row in enumerate(rows, start=2):
        equipment = (row.get("equipment") or "unknown").strip() or "unknown"
        review_status = (row.get("review_status") or "").strip().lower()
        image_path = _resolve_image_path(row.get("image_path", ""), root)
        exists = image_path.exists() and image_path.is_file()

        bucket = by_equipment.setdefault(
            equipment,
            {"total": 0, "available": 0, "approved": 0, "missing": 0, "fault_types": {}},
        )
        bucket["total"] += 1
        fault_type = (row.get("fault_type") or "unknown").strip() or "unknown"
        bucket["fault_types"][fault_type] = bucket["fault_types"].get(fault_type, 0) + 1

        required_blank = [
            column
            for column in REQUIRED_COLUMNS
            if column in fieldnames and not (row.get(column) or "").strip()
        ]
        if required_blank:
            invalid_rows.append(
                {
                    "line": index,
                    "id": row.get("id", ""),
                    "reason": "blank_required_fields",
                    "fields": required_blank,
                }
            )

        if exists:
            available += 1
            bucket["available"] += 1
            if review_status == "approved":
                approved += 1
                bucket["approved"] += 1
        else:
            bucket["missing"] += 1
            missing_paths.append(row.get("image_path", ""))

    missing_equipment = sorted(REQUIRED_EQUIPMENT - set(by_equipment))
    ready = (
        available >= required_images
        and approved >= required_images
        and not missing_columns
        and not invalid_rows
        and not missing_equipment
    )
    return {
        "exists": True,
        "manifest": str(manifest),
        "required_images": required_images,
        "total": len(rows),
        "available_images": available,
        "approved_images": approved,
        "missing_images": len(rows) - available,
        "invalid_rows": invalid_rows,
        "missing_columns": missing_columns,
        "by_equipment": by_equipment,
        "missing_equipment": missing_equipment,
        "missing_paths": missing_paths,
        "ready": ready,
    }


def write_markdown_report(result: dict, output_path: Path | str = DEFAULT_REPORT) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Multimodal Image Evaluation Status",
        "",
        f"ready: `{result['ready']}`",
        f"manifest: `{result['manifest']}`",
        "",
        "## Gate",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| required_images | {result['required_images']} |",
        f"| manifest_rows | {result['total']} |",
        f"| available_images | {result['available_images']} |",
        f"| approved_images | {result['approved_images']} |",
        f"| missing_images | {result['missing_images']} |",
        "",
        "## Equipment Coverage",
        "",
        "| Equipment | Rows | Available | Approved | Missing |",
        "|---|---:|---:|---:|---:|",
    ]
    for equipment, item in sorted(result["by_equipment"].items()):
        lines.append(
            f"| `{equipment}` | {item['total']} | {item['available']} | "
            f"{item['approved']} | {item['missing']} |"
        )

    lines.extend(["", "## Missing Resources", ""])
    if result["missing_paths"]:
        lines.append("missing_paths:")
        lines.extend(f"- `{path}`" for path in result["missing_paths"][:80])
    else:
        lines.append("- None")

    if result["missing_columns"]:
        lines.extend(["", "missing_columns:"])
        lines.extend(f"- `{column}`" for column in result["missing_columns"])

    if result["invalid_rows"]:
        lines.extend(["", "invalid_rows:", "", "```json"])
        lines.append(json.dumps(result["invalid_rows"], ensure_ascii=False, indent=2))
        lines.append("```")

    lines.extend(["", "## Raw Result", "", "```json"])
    lines.append(json.dumps(result, ensure_ascii=False, indent=2))
    lines.append("```")

    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize multimodal image evaluation assets.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = summarize_manifest(args.manifest)
    write_markdown_report(result, args.report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "ready": result["ready"],
                    "required_images": result["required_images"],
                    "available_images": result["available_images"],
                    "approved_images": result["approved_images"],
                    "missing_images": result["missing_images"],
                    "report": str(args.report),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
