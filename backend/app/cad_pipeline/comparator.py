from __future__ import annotations

from typing import Any


def compare_candidate_to_observation(observation: dict[str, Any], spec: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    observed = set(observation.get("component_keys") or [])
    specified = set(spec.get("component_keys") or [])
    matched = sorted(observed & specified)
    missing = sorted(observed - specified)
    render_count = sum(1 for item in (manifest.get("renders") or {}).values() if item.get("exists"))
    cad_count = sum(1 for item in (manifest.get("cad_files") or {}).values() if item.get("exists"))
    score = round(min(0.98, 0.35 + 0.08 * len(matched) + 0.04 * render_count + 0.03 * cad_count), 2)
    status = "pass" if score >= 0.78 and not missing else "needs_review" if score >= 0.5 else "reject"
    return {
        "schema_version": "candidate-cad-compare-v1",
        "provider": "rule_vlm_compare_cache",
        "status": status,
        "similarity_score": score,
        "matched_component_keys": matched,
        "missing_component_keys": missing,
        "hallucinated_component_keys": sorted(specified - observed),
        "render_views_checked": [key for key, item in (manifest.get("renders") or {}).items() if item.get("exists")],
        "review_required": True,
        "notes": "Cached rule/VLM proxy. Mechanical review is required before promotion.",
    }
