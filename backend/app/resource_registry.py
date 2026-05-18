from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .database import PROJECT_ROOT

VERIFIED_RESOURCES = PROJECT_ROOT / "data" / "sources" / "verified_resources.json"
THREE_D_VERIFICATION = PROJECT_ROOT / "data" / "3d" / "authorized_models" / "verification_report.json"


def _load_3d_asset_resources() -> list[dict[str, Any]]:
    if not THREE_D_VERIFICATION.exists():
        return []
    try:
        payload = json.loads(THREE_D_VERIFICATION.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [
            {
                "id": "authorized-3d-assets",
                "type": "authorized_3d_asset",
                "title": "授权 3D 资产验证报告",
                "verify_status": "failed",
                "usage": "3D 检修工位主演示资产",
                "errors": ["verification_report_json_invalid"],
            }
        ]
    resources: list[dict[str, Any]] = []
    for item in payload.get("resources", []):
        glb = item.get("glb", {})
        resources.append(
            {
                "id": item.get("id", ""),
                "type": "authorized_3d_asset",
                "title": "本地授权 CAD/GLB 检修模型",
                "verify_status": item.get("status", "missing"),
                "usage": "3D 检修数字孪生工位；用于部件定位、SOP 空间绑定和授权来源展示",
                "license": item.get("license", ""),
                "checked_files": item.get("checked_files", []),
                "glb": {
                    "bytes": glb.get("bytes", 0),
                    "nodes": glb.get("nodes", 0),
                    "meshes": glb.get("meshes", 0),
                    "node_names": glb.get("node_names", []),
                },
                "errors": item.get("errors", []),
                "warnings": item.get("warnings", []),
            }
        )
    return resources


def load_resource_verification() -> dict[str, Any]:
    if not VERIFIED_RESOURCES.exists():
        return {
            "generated_at": "",
            "summary": {
                "total": 0,
                "verified": 0,
                "blocked": 0,
                "failed": 0,
                "critical_failures": [],
            },
            "resources": _load_3d_asset_resources(),
        }
    try:
        payload = json.loads(VERIFIED_RESOURCES.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "generated_at": "",
            "summary": {
                "total": 0,
                "verified": 0,
                "blocked": 0,
                "failed": 1,
                "critical_failures": ["verified_resources_json_invalid"],
            },
            "resources": _load_3d_asset_resources(),
        }
    three_d_resources = _load_3d_asset_resources()
    if three_d_resources:
        payload["three_d_assets"] = three_d_resources
        payload["resources"] = [*three_d_resources, *payload.get("resources", [])]
        summary = dict(payload.get("summary", {}))
        summary["authorized_3d_assets"] = len(three_d_resources)
        summary["authorized_3d_verified"] = sum(1 for item in three_d_resources if item.get("verify_status") == "passed")
        payload["summary"] = summary
    return payload


def resource_verification_summary() -> dict[str, Any]:
    payload = load_resource_verification()
    resources = payload.get("resources", [])
    official = next(
        (item for item in resources if item.get("type") == "official_sample_manual"),
        None,
    )
    three_d_assets = [item for item in resources if item.get("type") == "authorized_3d_asset"]
    return {
        "generated_at": payload.get("generated_at", ""),
        "summary": payload.get("summary", {}),
        "official_sample_manual": {
            "id": official.get("id", "") if official else "",
            "title": official.get("title", "") if official else "",
            "status": official.get("verify_status", "missing") if official else "missing",
            "pages": (official.get("checks", {}) or {}).get("pages", 0) if official else 0,
            "keyword_hits": (official.get("checks", {}) or {}).get("keyword_hits", []) if official else [],
        },
        "authorized_3d_assets": {
            "count": len(three_d_assets),
            "verified": sum(1 for item in three_d_assets if item.get("verify_status") == "passed"),
            "ids": [item.get("id", "") for item in three_d_assets],
        },
    }
