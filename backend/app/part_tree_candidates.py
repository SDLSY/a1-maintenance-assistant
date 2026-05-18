from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .database import PROJECT_ROOT

PART_TREE_DIR = PROJECT_ROOT / "data" / "3d" / "part_tree_candidates"
PART_TREE_MANIFEST = PART_TREE_DIR / "candidate_manifest.json"
PART_TREE_REPORT = PART_TREE_DIR / "verification_report.json"


def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _classification_family(classification: str) -> str:
    if classification == "assembly_tree":
        return "assembly_tree"
    if classification in {"multi_solid_cad", "freecad_feature_tree", "freecad_parametric_or_multi_object"}:
        return "multi_solid_or_feature_tree"
    return "unknown"


def _candidate_quality(item: dict[str, Any]) -> str:
    status = item.get("status")
    classification = item.get("analysis", {}).get("classification", "")
    if status != "passed":
        return "blocked"
    if classification == "assembly_tree":
        return "可直接进入对象级拆分验证"
    if classification == "multi_solid_cad":
        return "可进入多实体分组和对象命名"
    if classification.startswith("freecad"):
        return "可进入 FreeCAD 特征树拆分和命名"
    return "仅作参考"


def load_part_tree_candidates(equipment: str = "") -> dict[str, Any]:
    manifest = _read_json(
        PART_TREE_MANIFEST,
        {
            "schema_version": "missing",
            "policy": {},
            "candidates": [],
            "blocked_sources": [],
        },
    )
    report = _read_json(
        PART_TREE_REPORT,
        {
            "schema_version": "missing",
            "summary": {
                "total": 0,
                "passed": 0,
                "blocked": 0,
                "failed": 0,
                "assembly_tree": 0,
                "multi_solid_or_feature_tree": 0,
            },
            "results": [],
        },
    )
    manifest_by_id = {item.get("id"): item for item in manifest.get("candidates", [])}
    report_results = report.get("results", [])

    candidates: list[dict[str, Any]] = []
    for result in report_results:
        candidate_id = result.get("id")
        source = manifest_by_id.get(candidate_id, {})
        merged = {
            "id": candidate_id,
            "equipment": result.get("equipment") or source.get("equipment") or "unknown",
            "title": result.get("title") or source.get("title") or candidate_id,
            "source": source.get("source", ""),
            "source_url": result.get("source_url") or source.get("source_url", ""),
            "local_path": result.get("local_path") or source.get("local_path", ""),
            "download_method": source.get("download_method", ""),
            "license": result.get("license") or source.get("license", ""),
            "license_url": source.get("license_url", ""),
            "intended_use": result.get("intended_use") or source.get("intended_use", ""),
            "accepted_classifications": source.get("accepted_classifications", []),
            "status": result.get("status", "unknown"),
            "errors": result.get("errors", []),
            "warnings": result.get("warnings", []),
            "bytes": result.get("bytes", 0),
            "sha256": result.get("sha256", ""),
            "suffix": result.get("suffix", ""),
            "analysis": result.get("analysis", {}),
        }
        merged["classification_family"] = _classification_family(
            str(merged["analysis"].get("classification", ""))
        )
        merged["quality_gate"] = _candidate_quality(merged)
        if equipment and merged["equipment"] != equipment:
            continue
        candidates.append(merged)

    equipment_summary: dict[str, dict[str, int]] = {}
    for item in candidates:
        bucket = equipment_summary.setdefault(
            item["equipment"],
            {"total": 0, "passed": 0, "assembly_tree": 0, "multi_solid_or_feature_tree": 0},
        )
        bucket["total"] += 1
        if item["status"] == "passed":
            bucket["passed"] += 1
        family = item["classification_family"]
        if family in bucket:
            bucket[family] += 1

    return {
        "schema_version": report.get("schema_version", manifest.get("schema_version", "missing")),
        "generated_at": report.get("generated_at", manifest.get("updated_at", "")),
        "manifest_path": str(PART_TREE_MANIFEST.relative_to(PROJECT_ROOT)),
        "report_path": str(PART_TREE_REPORT.relative_to(PROJECT_ROOT)),
        "policy": manifest.get("policy", {}),
        "summary": report.get("summary", {}),
        "equipment_summary": equipment_summary,
        "truth_statement": "未找到原生装配树；当前候选为 FreeCAD 特征树或 STEP 多实体模型，适合继续做对象命名和 sidecar 绑定验证。",
        "next_steps": [
            "优先把 Marathon 电机、离心泵、发动机 STEP 做实体分组和中文部件命名。",
            "对 FreeCAD FCStd 模型保留特征树截图、对象名、许可证和 SHA256，作为可追溯证据。",
            "只有完成对象级命名和侧车标注的资源才进入 3D 主演示。",
        ],
        "candidates": candidates,
        "blocked_sources": manifest.get("blocked_sources", []),
    }
