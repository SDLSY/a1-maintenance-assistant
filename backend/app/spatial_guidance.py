from __future__ import annotations

import json
import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STANDARD_MODEL_MANIFEST = PROJECT_ROOT / "data" / "3d" / "standard_models.json"
AUTHORIZED_MODEL_MANIFEST = PROJECT_ROOT / "data" / "3d" / "authorized_models" / "manifest.json"
SEMANTIC_SIDECAR_DIR = PROJECT_ROOT / "data" / "3d" / "semantic_sidecars"


def _json_loads(value: str, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return default


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _project_file(path_value: str | None) -> Path | None:
    if not path_value:
        return None
    candidate = Path(str(path_value))
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _sha256(path: Path | None) -> str:
    if not path or not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _cad_format(path_value: str | None, fallback: str = "") -> str:
    suffix = Path(str(path_value or "")).suffix.lower()
    return {
        ".step": "STEP",
        ".stp": "STEP",
        ".fcstd": "FreeCAD FCStd",
        ".glb": "GLB",
        ".gltf": "GLTF",
        ".stl": "STL",
        ".obj": "OBJ scan mesh",
        ".json": "JSON",
    }.get(suffix, fallback or "unknown")


def _file_evidence(path_value: str | None, *, role: str, public_url: str = "") -> dict[str, Any]:
    path = _project_file(path_value)
    exists = bool(path and path.exists())
    return {
        "role": role,
        "path": path_value or "",
        "format": _cad_format(path_value),
        "public_url": public_url,
        "preview_url": "",
        "download_url": "",
        "exists": exists,
        "bytes": path.stat().st_size if exists and path else 0,
        "sha256": _sha256(path),
    }


def _build_cad_bridge(
    model: dict[str, Any],
    components: list[dict[str, Any]],
    sop_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    conversion_path = _project_file(model.get("conversion_report"))
    sidecar_path = _project_file(model.get("sidecar_path"))
    conversion = _read_json(conversion_path, {}) if conversion_path else {}
    sidecar = _read_json(sidecar_path, {}) if sidecar_path else {}
    node_bindings = model.get("node_bindings", {}) or {}
    binding_by_component = {
        key: value for key, value in node_bindings.items() if isinstance(value, dict)
    }
    sop_count_by_component: dict[str, int] = {}
    for binding in sop_bindings or []:
        key = str(binding.get("component_key") or "")
        if key:
            sop_count_by_component[key] = sop_count_by_component.get(key, 0) + 1

    model_id = model.get("id", "")
    file_url_base = f"/api/3d/models/{model_id}/files" if model_id else ""
    cad_source = _file_evidence(model.get("source_cad_path"), role="source_cad")
    glb_viewer = _file_evidence(
        model.get("processed_mesh_path"),
        role="web_viewer_glb",
        public_url=model.get("processed_mesh_url") or model.get("mesh_path", ""),
    )
    sidecar_evidence = _file_evidence(model.get("sidecar_path"), role="semantic_sidecar")
    conversion_evidence = _file_evidence(model.get("conversion_report"), role="conversion_report")
    if file_url_base:
        if cad_source["path"]:
            cad_source["preview_url"] = f"{file_url_base}/source-cad/preview"
            cad_source["download_url"] = f"{file_url_base}/source-cad"
        if glb_viewer["path"]:
            glb_viewer["preview_url"] = f"{file_url_base}/glb/preview"
            glb_viewer["download_url"] = f"{file_url_base}/glb"
        if sidecar_evidence["path"]:
            sidecar_evidence["preview_url"] = f"{file_url_base}/sidecar/preview"
            sidecar_evidence["download_url"] = f"{file_url_base}/sidecar"
        if conversion_evidence["path"]:
            conversion_evidence["preview_url"] = f"{file_url_base}/conversion-report/preview"
            conversion_evidence["download_url"] = f"{file_url_base}/conversion-report"
    conversion_evidence["toolchain"] = conversion.get("toolchain", {})
    conversion_evidence["usage_note"] = conversion.get("usage_note", "")

    part_semantics = sidecar.get("part_semantics") or sidecar.get("components") or []
    sidecar_evidence["binding_mode"] = node_bindings.get("binding_mode", "semantic_hotspot_overlay")
    sidecar_evidence["component_count"] = len(part_semantics) or len(components)
    sidecar_evidence["object_level_binding"] = bool(node_bindings.get("object_level_binding"))
    sidecar_evidence["exact_cad_face_binding"] = bool(node_bindings.get("exact_cad_face_binding"))

    component_bindings = []
    for component in components:
        key = component.get("component_key", "")
        binding = binding_by_component.get(key, {})
        component_bindings.append(
            {
                "component_key": key,
                "label": component.get("label", key),
                "cad_node": binding.get("node") or binding.get("cad_node") or node_bindings.get("cad_mesh", ""),
                "cad_node_label": f"{component.get('label', key)}结构节点",
                "hotspot": binding.get("hotspot") or component.get("hotspot", {}),
                "exact_face_binding": bool(binding.get("exact_face_binding")),
                "manual_keywords": component.get("manual_keywords", []),
                "sop_step_count": sop_count_by_component.get(key, 0),
            }
        )

    return {
        "title": "结构模型双证据链",
        "model_id": model.get("id", ""),
        "model_title": model.get("title", ""),
        "viewer_mode": model.get("viewer_mode", ""),
        "asset_status": model.get("asset_status", ""),
        "license": model.get("license", {}),
        "cad_source": cad_source,
        "glb_viewer": glb_viewer,
        "sidecar": sidecar_evidence,
        "conversion": conversion_evidence,
        "trace_chain": [
            {
                "stage": "source_cad",
                "label": "结构原件",
                "path": cad_source["path"],
                "status": "verified" if cad_source["exists"] else "missing",
                "explanation": "工程来源文件，用于证明模型来源、授权和可追溯性。",
            },
            {
                "stage": "mesh_conversion",
                "label": "网页三维模型",
                "path": glb_viewer["path"],
                "status": "ready" if glb_viewer["exists"] else "missing",
                "explanation": "从结构原件转换出的浏览器交互模型，用于旋转、剖视、爆炸和高亮。",
            },
            {
                "stage": "semantic_sidecar",
                "label": "辅助标注",
                "path": sidecar_evidence["path"],
                "status": "ready" if sidecar_evidence["exists"] else "missing",
                "explanation": "把结构模型节点映射为业务部件、故障标签、安全项和手册关键词。",
            },
            {
                "stage": "sop_binding",
                "label": "作业步骤部件绑定",
                "path": "",
                "status": "ready" if sop_bindings else "waiting_for_guidance",
                "explanation": "将检修步骤绑定到部件标识，点击步骤即可定位三维部件并回看结构来源。",
            },
        ],
        "component_bindings": component_bindings,
        "limitations": [
            "网页端展示三维模型，不直接原生渲染工程原件；结构原件作为工程来源证据和转换依据展示。",
            "当前不声称 CAD 面级尺寸测量，安全放行仍以 SOP、手册证据和人工确认为准。",
            "若需要真正结构模型浏览器，应后续接入 OCCT WebAssembly 或后端 FreeCAD/OCCT 转换服务。",
        ],
    }


def _standard_models() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = _read_json(
        STANDARD_MODEL_MANIFEST,
        {"version": "missing", "license_note": "missing standard model manifest", "models": []},
    )
    models: list[dict[str, Any]] = []
    for model in manifest.get("models", []):
        item = dict(model)
        sidecar_path = SEMANTIC_SIDECAR_DIR / f"{item.get('id', '')}.sidecar.json"
        sidecar = _read_json(sidecar_path, {}) if sidecar_path.exists() else {}
        viewer = sidecar.get("viewer", {})
        if sidecar:
            item["title"] = sidecar.get("title", item.get("title", item.get("id", "")))
            item["viewer_mode"] = viewer.get("viewer_mode", item.get("viewer_mode", "semantic_overlay"))
            item["sidecar_path"] = str(sidecar_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            item["license"] = {
                "id": sidecar.get("license", {}).get("spdx_like", ""),
                "url": sidecar.get("license", {}).get("url", ""),
                "attribution": sidecar.get("license", {}).get("attribution", item.get("attribution", "")),
                "redistribution_allowed_with_attribution": sidecar.get("license", {}).get(
                    "redistribution_allowed_with_attribution", False
                ),
                "notes": sidecar.get("license", {}).get("notes", ""),
            }
            item["node_bindings"] = sidecar.get("node_bindings", item.get("node_bindings", {}))
            item["inspection_views"] = sidecar.get("inspection_views", item.get("inspection_views", []))
            item["explode_steps"] = sidecar.get("explode_steps", item.get("explode_steps", []))
            item["components"] = sidecar.get("components", item.get("components", []))
            item["asset_status"] = f"{item.get('asset_status', '')}; semantic_sidecar_ready"
        item.setdefault("viewer_mode", "external_embed" if item.get("embed_url") else "procedural_fallback")
        item.setdefault("processed_mesh_path", "")
        item.setdefault("processed_mesh_url", "")
        item.setdefault("source_cad_path", "")
        item.setdefault("sidecar_path", "")
        item.setdefault("conversion_report", "")
        item.setdefault("license", {})
        item.setdefault("node_bindings", {})
        item.setdefault("inspection_views", [])
        item.setdefault("explode_steps", [])
        models.append(item)
    return manifest, models


_BEARING_LABELS = {
    "outer_ring": "外圈滚道",
    "inner_ring": "内圈",
    "rolling_elements": "滚动体",
    "cage": "保持架",
    "seal_pair": "2RS 密封圈",
}

_BEARING_KEYWORDS = {
    "outer_ring": ["外圈", "外滚道", "滚道", "剥落", "点蚀", "磨损", "蓝变", "异响", "温升"],
    "inner_ring": ["内圈", "内滚道", "轴颈", "配合松动", "蠕动", "磨损", "异响"],
    "rolling_elements": ["滚动体", "钢球", "球", "点蚀", "压痕", "剥落", "异响", "卡滞"],
    "cage": ["保持架", "铆钉", "断裂", "变形", "擦伤", "卡滞"],
    "seal_pair": ["密封", "密封圈", "油脂", "润滑脂", "泄漏", "污染", "进水", "进尘"],
}


def _authorized_components(sidecar: dict[str, Any]) -> list[dict[str, Any]]:
    bindings = sidecar.get("node_bindings", {})
    components: list[dict[str, Any]] = []
    for semantic in sidecar.get("part_semantics", []):
        key = semantic.get("id", "")
        binding = bindings.get(key, {}) if isinstance(bindings, dict) else {}
        hotspot = binding.get("hotspot", [0, 0, 0])
        aliases = [str(alias) for alias in semantic.get("aliases", []) if alias]
        focus_tags = list(semantic.get("inspection_focus", []))
        tags = list(semantic.get("fault_tags", [])) + focus_tags + _BEARING_KEYWORDS.get(key, [])
        manual_keywords = aliases + list(semantic.get("manual_keywords", [])) + tags + [
            semantic.get("label", ""),
            semantic.get("name", ""),
            key,
        ]
        safety_tags = semantic.get("safety_tags") or ["LOTO", "PPE", "防误启动"]
        components.append(
            {
                "component_key": key,
                "label": semantic.get("label") or _BEARING_LABELS.get(key, semantic.get("name", key)),
                "geometry": {
                    "hotspot_only": True,
                    "source_node": binding.get("node", bindings.get("cad_mesh", "")),
                    "binding_mode": bindings.get("binding_mode", "semantic_hotspot_overlay"),
                    "object_level_binding": bool(bindings.get("object_level_binding")),
                    "exact_cad_face_binding": bindings.get("exact_cad_face_binding", False),
                },
                "hotspot": {"x": hotspot[0], "y": hotspot[1], "z": hotspot[2]} if len(hotspot) == 3 else {},
                "fault_tags": tags,
                "safety_tags": safety_tags,
                "aliases": aliases,
                "manual_keywords": [keyword for keyword in manual_keywords if keyword],
            }
        )
    return components


def _authorized_models() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = _read_json(AUTHORIZED_MODEL_MANIFEST, {"schema_version": "missing", "resources": []})
    models: list[dict[str, Any]] = []
    for resource in manifest.get("resources", []):
        sidecar_rel = resource.get("sidecar", "")
        sidecar_path = AUTHORIZED_MODEL_MANIFEST.parent / sidecar_rel
        sidecar = _read_json(sidecar_path, {})
        viewer = sidecar.get("viewer", {})
        license_info = sidecar.get("license", {})
        source = sidecar.get("source", {})
        title = resource.get("title", sidecar.get("title", resource["id"]))
        model = {
            "id": resource["id"],
            "equipment": resource.get("equipment", "bearing"),
            "model_code": resource.get("model_code", sidecar.get("model_code", resource["id"])),
            "title": f"授权本地 CAD：{title}",
            "source_type": "authorized_cad",
            "viewer_mode": resource.get("viewer_mode", viewer.get("viewer_mode", "local_glb")),
            "mesh_path": resource.get("processed_mesh_url", viewer.get("processed_mesh_url", "")),
            "processed_mesh_path": resource.get("processed_mesh_path", viewer.get("processed_mesh_path", "")),
            "processed_mesh_url": resource.get("processed_mesh_url", viewer.get("processed_mesh_url", "")),
            "source_cad_path": resource.get("source_cad_path", viewer.get("source_cad_path", "")),
            "sidecar_path": resource.get("sidecar_path", viewer.get("sidecar_path", "")),
            "conversion_report": resource.get("conversion_report", viewer.get("conversion_report", "")),
            "preview_path": "",
            "source_url": resource.get("source_page", source.get("source_page", "")),
            "embed_url": "",
            "attribution": license_info.get("attribution", ""),
            "asset_status": resource.get("asset_status", "authorized_local_glb"),
            "license": {
                "id": resource.get("license", license_info.get("spdx_like", "")),
                "url": resource.get("license_url", license_info.get("url", "")),
                "attribution": license_info.get("attribution", ""),
                "redistribution_allowed_with_attribution": license_info.get(
                    "redistribution_allowed_with_attribution", True
                ),
            },
            "node_bindings": resource.get("node_bindings", sidecar.get("node_bindings", {})),
            "inspection_views": sidecar.get("inspection_views", []),
            "explode_steps": sidecar.get("explode_steps", []),
            "components": _authorized_components(sidecar),
        }
        models.append(model)
    return manifest, models


def _all_model_manifests() -> tuple[str, str, list[dict[str, Any]]]:
    standard_manifest, standard = _standard_models()
    authorized_manifest, authorized = _authorized_models()
    version = f"{standard_manifest.get('version', 'standard')}+authorized-{authorized_manifest.get('updated_at', 'missing')}"
    license_note = standard_manifest.get("license_note", "")
    return version, license_note, [*authorized, *standard]


def ensure_standard_3d_models(conn: sqlite3.Connection) -> dict:
    version, license_note, models = _all_model_manifests()
    now = datetime.now(UTC).isoformat(timespec="seconds")
    inserted_models = 0
    inserted_components = 0
    for model in models:
        cursor = conn.execute(
            """
            INSERT INTO standard_3d_models
            (id, equipment, model_code, title, source_type, mesh_path, preview_path,
             source_url, embed_url, attribution, asset_status, viewer_mode,
             processed_mesh_path, processed_mesh_url, source_cad_path, sidecar_path,
             conversion_report, license_json, node_bindings_json, inspection_views_json,
             explode_steps_json, version, license_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                equipment = excluded.equipment,
                model_code = excluded.model_code,
                title = excluded.title,
                source_type = excluded.source_type,
                mesh_path = excluded.mesh_path,
                preview_path = excluded.preview_path,
                source_url = excluded.source_url,
                embed_url = excluded.embed_url,
                attribution = excluded.attribution,
                asset_status = excluded.asset_status,
                viewer_mode = excluded.viewer_mode,
                processed_mesh_path = excluded.processed_mesh_path,
                processed_mesh_url = excluded.processed_mesh_url,
                source_cad_path = excluded.source_cad_path,
                sidecar_path = excluded.sidecar_path,
                conversion_report = excluded.conversion_report,
                license_json = excluded.license_json,
                node_bindings_json = excluded.node_bindings_json,
                inspection_views_json = excluded.inspection_views_json,
                explode_steps_json = excluded.explode_steps_json,
                version = excluded.version,
                license_note = excluded.license_note
            """,
            (
                model["id"],
                model["equipment"],
                model.get("model_code", ""),
                model["title"],
                model.get("source_type", "procedural"),
                model.get("mesh_path", ""),
                model.get("preview_path", ""),
                model.get("source_url", ""),
                model.get("embed_url", ""),
                model.get("attribution", ""),
                model.get("asset_status", ""),
                model.get("viewer_mode", ""),
                model.get("processed_mesh_path", ""),
                model.get("processed_mesh_url", ""),
                model.get("source_cad_path", ""),
                model.get("sidecar_path", ""),
                model.get("conversion_report", ""),
                _json_dumps(model.get("license", {})),
                _json_dumps(model.get("node_bindings", {})),
                _json_dumps(model.get("inspection_views", [])),
                _json_dumps(model.get("explode_steps", [])),
                version,
                license_note,
                now,
            ),
        )
        inserted_models += cursor.rowcount
        conn.execute("DELETE FROM model_components WHERE model_id = ?", (model["id"],))
        for component in model.get("components", []):
            cursor = conn.execute(
                """
                INSERT INTO model_components
                (model_id, component_key, label, geometry_json, hotspot_json,
                 fault_tags, safety_tags, manual_keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model["id"],
                    component["component_key"],
                    component["label"],
                    _json_dumps(component.get("geometry", {})),
                    _json_dumps(component.get("hotspot", {})),
                    _json_dumps(component.get("fault_tags", [])),
                    _json_dumps(component.get("safety_tags", [])),
                    _json_dumps(component.get("manual_keywords", [])),
                ),
            )
            inserted_components += cursor.rowcount
    conn.commit()
    return {
        "standard_manifest": str(STANDARD_MODEL_MANIFEST),
        "authorized_manifest": str(AUTHORIZED_MODEL_MANIFEST),
        "models_inserted": inserted_models,
        "components_inserted": inserted_components,
        "model_count": conn.execute("SELECT COUNT(*) AS c FROM standard_3d_models").fetchone()["c"],
        "component_count": conn.execute("SELECT COUNT(*) AS c FROM model_components").fetchone()["c"],
    }


def _viewer_mode(row: dict[str, Any]) -> str:
    if row.get("viewer_mode"):
        return row["viewer_mode"]
    if row.get("processed_mesh_url") or row.get("processed_mesh_path"):
        return "local_glb"
    if row.get("embed_url"):
        return "external_embed"
    return "procedural_fallback"


def _model_summary(row: dict[str, Any]) -> dict[str, Any]:
    row["viewer_mode"] = _viewer_mode(row)
    row["license"] = _json_loads(row.pop("license_json", "{}"), {})
    row["node_bindings"] = _json_loads(row.pop("node_bindings_json", "{}"), {})
    row["inspection_views"] = _json_loads(row.pop("inspection_views_json", "[]"), [])
    row["explode_steps"] = _json_loads(row.pop("explode_steps_json", "[]"), [])
    if row["viewer_mode"] == "local_glb" and row.get("processed_mesh_url"):
        row["mesh_path"] = row["processed_mesh_url"]
    return row


def list_standard_models(conn: sqlite3.Connection, equipment: str = "") -> list[dict]:
    ensure_standard_3d_models(conn)
    if equipment:
        rows = conn.execute(
            """
            SELECT * FROM standard_3d_models
            WHERE equipment = ?
            ORDER BY
                CASE source_type WHEN 'authorized_cad' THEN 0 WHEN 'scan_mesh_model' THEN 0 WHEN 'candidate_cad' THEN 3 ELSE 1 END,
                CASE viewer_mode WHEN 'local_glb' THEN 0 WHEN 'external_embed' THEN 1 ELSE 2 END,
                id
            """,
            (equipment,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM standard_3d_models
            ORDER BY
                equipment,
                CASE source_type WHEN 'authorized_cad' THEN 0 WHEN 'scan_mesh_model' THEN 0 WHEN 'candidate_cad' THEN 3 ELSE 1 END,
                CASE viewer_mode WHEN 'local_glb' THEN 0 WHEN 'external_embed' THEN 1 ELSE 2 END,
                id
            """
        ).fetchall()
    return [_model_summary(dict(row)) for row in rows]


def _component_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "model_id": row["model_id"],
        "component_key": row["component_key"],
        "label": row["label"],
        "geometry": _json_loads(row["geometry_json"], {}),
        "hotspot": _json_loads(row["hotspot_json"], {}),
        "fault_tags": _json_loads(row["fault_tags"], []),
        "safety_tags": _json_loads(row["safety_tags"], []),
        "manual_keywords": _json_loads(row["manual_keywords"], []),
    }


def get_standard_model(conn: sqlite3.Connection, model_id: str) -> dict | None:
    ensure_standard_3d_models(conn)
    row = conn.execute("SELECT * FROM standard_3d_models WHERE id = ?", (model_id,)).fetchone()
    if not row:
        return None
    components = conn.execute(
        """
        SELECT * FROM model_components
        WHERE model_id = ?
        ORDER BY id
        """,
        (model_id,),
    ).fetchall()
    payload = _model_summary(dict(row))
    payload["components"] = [_component_from_row(component) for component in components]
    local_asset = payload.get("viewer_mode") == "local_glb"
    semantic_ready = bool(payload.get("node_bindings", {}).get("semantic_sidecar_ready"))
    payload["limitations"] = [
        "3D 模型用于空间理解、部件定位和作业指引，不作为尺寸测量依据。",
        "本地 GLB 的授权来源、原始 CAD、转换日志和 sidecar 均可追溯。"
        if local_asset
        else "外嵌模型不重新分发原始 mesh；本地仅保存语义 sidecar、热点和来源/署名信息。",
        "该设备已补齐标准化部件语义标识。"
        if semantic_ready
        else "该设备尚未补齐完整语义 sidecar，部件定位需要人工复核。",
        "one-photo/multi-photo 重建结果仅作辅助理解，安全放行以 SOP、手册证据和人工确认为准。",
    ]
    payload["cad_bridge"] = _build_cad_bridge(payload, payload["components"])
    return payload


def _select_model(conn: sqlite3.Connection, equipment: str, model_code: str = "") -> dict:
    ensure_standard_3d_models(conn)
    candidates = list_standard_models(conn, equipment)
    if not candidates:
        candidates = list_standard_models(conn)
    if not candidates:
        raise RuntimeError("standard 3D model manifest is empty")
    normalized_model = (model_code or "").lower()
    stable_candidates = [
        candidate for candidate in candidates
        if str(candidate.get("source_type") or "") != "candidate_cad"
    ]
    candidate_pool = stable_candidates or candidates
    for candidate in candidate_pool:
        code = str(candidate.get("model_code") or "").lower()
        if code and normalized_model and (code in normalized_model or normalized_model in code):
            return get_standard_model(conn, candidate["id"]) or candidate
    return get_standard_model(conn, candidate_pool[0]["id"]) or candidate_pool[0]


def _visual_terms(visual_asset: dict | None) -> list[str]:
    if not visual_asset:
        return []
    analysis = visual_asset.get("analysis", {})
    terms: list[str] = [
        str(analysis.get("caption") or visual_asset.get("caption") or ""),
        str(analysis.get("ocr_text") or ""),
    ]
    for field in ("component_candidates", "defect_labels"):
        for item in analysis.get(field, []) or []:
            if isinstance(item, dict):
                terms.append(str(item.get("label") or item.get("id") or ""))
            else:
                terms.append(str(item))
    for item in analysis.get("retrieval_keywords", []) or []:
        terms.append(str(item))
    return [term for term in terms if term]


def _hit_text(hit: Any) -> str:
    if isinstance(hit, dict):
        return str(hit.get("content") or hit.get("text") or "")
    return str(getattr(hit, "content", "") or getattr(hit, "text", "") or "")


def _score_component(component: dict, text: str, visual_terms: list[str]) -> tuple[float, list[str]]:
    haystack = " ".join([text, *visual_terms]).lower()
    reasons: list[str] = []
    score = 0.08
    for tag in component.get("fault_tags", []):
        tag_text = str(tag).lower()
        if tag_text and tag_text in haystack:
            score += 0.22
            reasons.append(f"命中故障/视觉标签：{tag}")
    for keyword in component.get("manual_keywords", []):
        keyword_text = str(keyword).lower()
        if keyword_text and keyword_text in haystack:
            score += 0.16
            reasons.append(f"命中手册关键词：{keyword}")
    label = str(component.get("label") or "")
    if label and label.lower() in haystack:
        score += 0.26
        reasons.append(f"直接命中部件：{label}")
    return min(score, 0.98), reasons[:4]


def _default_component_keys(equipment: str) -> list[str]:
    return {
        "motor": ["front_bearing_end", "end_cover"],
        "pump": ["pump_seal_zone", "pump_shaft"],
        "bearing": ["outer_ring", "rolling_elements"],
        "engine": ["spark_plug", "cylinder_head", "cylinder_block"],
    }.get(equipment, [])


def _safety_gate(sop: dict | None) -> dict:
    compliance = sop.get("compliance", []) if sop else []
    if not compliance:
        return {
            "status": "needs_confirmation",
            "label": "等待安全确认",
            "failed_count": 0,
            "required_checks": [],
            "blocking_reasons": ["尚未确认断电挂牌、PPE、防误启动等安全项"],
        }
    failed = [item for item in compliance if not item.get("passed")]
    return {
        "status": "blocked" if failed else "ready",
        "label": "禁止进入拆检" if failed else "允许进入受控检修",
        "failed_count": len(failed),
        "required_checks": compliance,
        "blocking_reasons": [item.get("label", "未通过安全项") for item in failed],
    }


def _default_required_safety_checks(equipment: str) -> list[dict[str, Any]]:
    base = [
        {"code": "LOTO", "label": "断电挂牌", "passed": False, "evidence": "进入拆检前必须完成能量隔离。"},
        {"code": "PPE", "label": "PPE 防护", "passed": False, "evidence": "佩戴护目镜、防割手套和防滑鞋。"},
        {"code": "NO_RESTART", "label": "防误启动", "passed": False, "evidence": "确认启动源隔离并设置告知牌。"},
        {"code": "CLEAN_AREA", "label": "清洁检修区", "passed": False, "evidence": "轴承拆检前清理油污、粉尘和松散异物。"},
        {"code": "ACCEPTANCE", "label": "复测验收", "passed": False, "evidence": "复装后记录噪声、振动和温升。"},
    ]
    if equipment == "pump":
        base.insert(3, {"code": "DEPRESSURIZE", "label": "泄压排液", "passed": False, "evidence": "确认无残余压力和介质喷溅风险。"})
    if equipment == "engine":
        base.insert(3, {"code": "COOL_DOWN", "label": "冷机确认", "passed": False, "evidence": "确认火花塞、气缸和冷却系统温度可接触。"})
    return base


def _safety_gate(sop: dict | None) -> dict:
    compliance = sop.get("compliance", []) if sop else []
    equipment = sop.get("equipment", "") if sop else ""
    if not compliance:
        required = _default_required_safety_checks(equipment)
        return {
            "status": "needs_confirmation",
            "label": "等待安全确认",
            "failed_count": len(required),
            "required_checks": required,
            "blocking_reasons": [item["label"] for item in required],
            "decision": "只能进入观察和定位，不允许进入拆检放行。",
        }
    normalized = [
        {
            "code": item.get("code", ""),
            "label": item.get("label", item.get("code", "安全项")),
            "passed": bool(item.get("passed")),
            "evidence": item.get("evidence", ""),
        }
        for item in compliance
    ]
    failed = [item for item in normalized if not item["passed"]]
    return {
        "status": "blocked" if failed else "ready",
        "label": "禁止进入拆检" if failed else "允许进入受控检修",
        "failed_count": len(failed),
        "required_checks": normalized,
        "blocking_reasons": [item["label"] for item in failed],
        "decision": "安全项未闭环，必须人工复核。" if failed else "可按 SOP 进入受控检修，并保留验收记录。",
    }


def _model_maturity(model: dict[str, Any]) -> dict[str, Any]:
    node_bindings = model.get("node_bindings", {}) or {}
    exact_binding = bool(node_bindings.get("exact_cad_face_binding"))
    object_binding = bool(node_bindings.get("object_level_binding") or exact_binding)
    local_glb = model.get("viewer_mode") == "local_glb"
    semantic_sidecar_ready = bool(node_bindings.get("semantic_sidecar_ready") or model.get("sidecar_path"))
    if not local_glb and semantic_sidecar_ready:
        return {
            "level": "v0_external_semantic",
            "label": "外部参考模型 + 本地语义热点标识",
            "local_asset": False,
            "object_level_binding": False,
            "binding_mode": node_bindings.get("binding_mode", "external_model_semantic_hotspot"),
            "limitations": [
                "当前没有本地授权 GLB/CAD，不能读取真实 mesh 节点。",
                "部件标识来自本地 sidecar 的语义热点，适合 SOP 导引和答辩展示。",
                "下一阶段应下载授权 CAD/GLB 后做对象命名和 sidecar 校准。",
            ],
            "next_upgrade": "下载授权 CAD/GLB 并完成对象级部件命名",
        }
    return {
        "level": "v1_authorized_semantic" if local_glb else "external_reference",
        "label": "授权 CAD + 命名对象热点绑定" if local_glb and object_binding else "授权 CAD + 语义热点绑定" if local_glb else "外部可引用模型",
        "local_asset": local_glb,
        "object_level_binding": object_binding,
        "binding_mode": node_bindings.get("binding_mode", "semantic_hotspot_overlay"),
        "limitations": [
            "当前 GLB 主体仍是来源 CAD/STL 的组合网格，部件定位依赖命名 marker 节点与 sidecar 热点。",
            "命名节点可用于答辩演示和 SOP 空间指引，不替代 CAD 面级尺寸测量。",
            "若进入下一阶段，应获取可分组件 CAD 或在 FreeCAD/Blender 中拆分为独立 mesh。",
        ]
        if local_glb and not exact_binding
        else [],
        "next_upgrade": "CAD 面级或独立零件级绑定" if local_glb and not exact_binding else "补充更多授权设备模型",
    }


def _step_phase(step_index: int, step: str) -> str:
    text = step or ""
    if step_index == 1 or any(word in text for word in ["断电", "挂牌", "PPE", "泄压", "冷机"]):
        return "安全确认"
    if any(word in text for word in ["拆", "检查", "旋转", "强光", "测量", "听诊"]):
        return "拆检诊断"
    if any(word in text for word in ["更换", "复装", "修复"]):
        return "处置复装"
    if any(word in text for word in ["验收", "试运行", "复测", "记录"]):
        return "验收归档"
    return "作业步骤"


def _enrich_sop_bindings(
    sop_bindings: list[dict[str, Any]],
    components: list[dict[str, Any]],
    highlighted: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    component_by_key = {item.get("component_key"): item for item in components}
    highlighted_keys = {item.get("component_key") for item in highlighted}
    enriched = []
    for item in sop_bindings:
        key = item.get("component_key", "")
        component = component_by_key.get(key, {})
        step = item.get("step", "")
        enriched.append(
            {
                **item,
                "component_label": component.get("label", key or "待定位部件"),
                "phase": _step_phase(int(item.get("step_index", 0) or 0), step),
                "risk_control": "必须完成安全闸门确认" if item.get("step_index") == 1 else "按引用证据执行并拍照留痕",
                "is_primary_hit": key in highlighted_keys,
            }
        )
    return enriched


def _default_spatial_steps(equipment: str, highlighted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = highlighted[0]["component_key"] if highlighted else ""
    if equipment == "bearing":
        return [
            {"step_index": 1, "step": "停机断电并挂锁挂牌，确认轴承座温度下降。", "component_key": primary},
            {"step_index": 2, "step": "检查 2RS 密封圈、润滑脂泄漏和污染进入痕迹。", "component_key": "seal_pair"},
            {"step_index": 3, "step": "旋转内圈并听诊，确认滚动体异响、卡滞或周期冲击。", "component_key": "rolling_elements"},
            {"step_index": 4, "step": "强光检查外圈/内圈滚道剥落、点蚀、压痕和蓝变。", "component_key": "outer_ring"},
            {"step_index": 5, "step": "更换或复装后进行空载试运行，复核振动、噪声和温升。", "component_key": primary},
        ]
    return []


def _build_scene_state(model: dict[str, Any], highlighted: list[dict[str, Any]], sop_bindings: list[dict[str, Any]]) -> dict:
    active = highlighted[0]["component_key"] if highlighted else ""
    views = model.get("inspection_views", [])
    recommended_view = views[0] if views else {"id": "default", "label": "默认视角"}
    for view in views:
        focus = set(view.get("focus_components", []))
        if active and active in focus:
            recommended_view = view
            break
    return {
        "viewer_mode": model.get("viewer_mode", "procedural_fallback"),
        "mesh_path": model.get("mesh_path", ""),
        "processed_mesh_url": model.get("processed_mesh_url", ""),
        "active_component_key": active,
        "highlighted_component_keys": [item["component_key"] for item in highlighted],
        "recommended_view": recommended_view,
        "explode": {"enabled": bool(sop_bindings), "step": 1 if sop_bindings else 0},
        "section": {
            "enabled": model.get("equipment") == "bearing",
            "axis": "z",
            "purpose": "展示轴承滚道、滚动体和密封侧的检查关系",
        },
        "timeline": [
            {
                "step_index": item["step_index"],
                "component_key": item["component_key"],
                "label": item["step"][:28],
            }
            for item in sop_bindings
        ],
    }


def _build_scene_state(model: dict[str, Any], highlighted: list[dict[str, Any]], sop_bindings: list[dict[str, Any]]) -> dict:
    active = highlighted[0]["component_key"] if highlighted else ""
    views = model.get("inspection_views", [])
    recommended_view = views[0] if views else {"id": "default", "label": "默认视角"}
    for view in views:
        focus = set(view.get("focus_components", []))
        if active and active in focus:
            recommended_view = view
            break
    maturity = _model_maturity(model)
    return {
        "viewer_mode": model.get("viewer_mode", "procedural_fallback"),
        "mesh_path": model.get("mesh_path", ""),
        "processed_mesh_url": model.get("processed_mesh_url", ""),
        "active_component_key": active,
        "highlighted_component_keys": [item["component_key"] for item in highlighted],
        "recommended_view": recommended_view,
        "explode": {"enabled": bool(sop_bindings), "step": 1 if sop_bindings else 0},
        "section": {
            "enabled": model.get("equipment") == "bearing",
            "axis": "z",
            "purpose": "展示轴承滚道、滚动体和密封侧的检查关系",
        },
        "timeline": [
            {
                "step_index": item["step_index"],
                "component_key": item["component_key"],
                "component_label": item.get("component_label", ""),
                "phase": item.get("phase", "作业步骤"),
                "label": item["step"][:28],
            }
            for item in sop_bindings
        ],
        "binding_quality": {
            "mode": maturity["binding_mode"],
            "binding_mode": maturity["binding_mode"],
            "object_level_binding": maturity["object_level_binding"],
            "explain": "当前为语义热点绑定，适合导引和答辩展示；不声称 CAD 面级测量。",
        },
    }


def build_spatial_guidance(
    conn: sqlite3.Connection,
    *,
    equipment: str,
    model_code: str = "",
    text: str = "",
    visual_asset: dict | None = None,
    sop: dict | None = None,
    manual_hits: list[Any] | None = None,
    case_hits: list[Any] | None = None,
) -> dict:
    model = _select_model(conn, equipment, model_code)
    components = model.get("components", [])
    visual_terms = _visual_terms(visual_asset)
    manual_text = " ".join(_hit_text(hit) for hit in manual_hits or [])
    case_text = " ".join(_hit_text(hit) for hit in case_hits or [])
    scoring_text = " ".join([text, model_code, manual_text, case_text])

    scored = []
    for component in components:
        score, reasons = _score_component(component, scoring_text, visual_terms)
        if reasons:
            scored.append((score, component, reasons))

    if not scored:
        defaults = set(_default_component_keys(model.get("equipment", equipment)))
        scored = [
            (0.52, component, ["按设备类型默认检修路径定位"])
            for component in components
            if component.get("component_key") in defaults
        ]
    if not scored and components:
        scored = [(0.44, components[0], ["未识别到明确部件，进入人工复核导引"])]

    scored.sort(key=lambda item: item[0], reverse=True)
    highlighted = []
    for score, component, reasons in scored[:3]:
        tone = "danger" if score >= 0.82 else "warning" if score >= 0.58 else "info"
        highlighted.append(
            {
                "component_key": component["component_key"],
                "label": component["label"],
                "confidence": round(score, 2),
                "tone": tone,
                "reason": "；".join(reasons),
                "geometry": component.get("geometry", {}),
                "hotspot": component.get("hotspot", {}),
                "safety_tags": component.get("safety_tags", []),
                "manual_keywords": component.get("manual_keywords", []),
            }
        )

    primary_key = highlighted[0]["component_key"] if highlighted else ""
    sop_steps = (sop or {}).get("sop_steps", [])
    highlighted_by_key = {item.get("component_key"): item for item in highlighted}
    component_search_order = [
        *highlighted,
        *[
            component
            for component in components
            if component.get("component_key") not in highlighted_by_key
        ],
    ]
    sop_bindings = []
    for index, step in enumerate(sop_steps, start=1):
        matched = ""
        for component in component_search_order:
            label = component.get("label", "")
            if label and label in step:
                matched = component["component_key"]
                break
        if not matched:
            for component in component_search_order:
                keywords = component.get("manual_keywords", [])
                if any(str(keyword) and str(keyword) in step for keyword in keywords):
                    matched = component["component_key"]
                    break
        if not matched:
            matched = primary_key
        sop_bindings.append({"step_index": index, "step": step, "component_key": matched})
    if not sop_bindings:
        sop_bindings = _default_spatial_steps(model.get("equipment", equipment), highlighted)
    sop_bindings = _enrich_sop_bindings(sop_bindings, components, highlighted)

    safety_context = {**(sop or {}), "equipment": model.get("equipment", equipment)}
    safety_gate = _safety_gate(safety_context)
    scene_state = _build_scene_state(model, highlighted, sop_bindings)
    model_maturity = _model_maturity(model)
    cad_bridge = _build_cad_bridge(model, components, sop_bindings)

    return {
        "mode": "standard_3d_guidance",
        "status": "ready" if highlighted else "needs_review",
        "model_id": model["id"],
        "model_title": model["title"],
        "model_code": model.get("model_code", ""),
        "equipment": model["equipment"],
        "source_type": model.get("source_type", "procedural"),
        "viewer_mode": model.get("viewer_mode", "procedural_fallback"),
        "mesh_path": model.get("mesh_path", ""),
        "processed_mesh_path": model.get("processed_mesh_path", ""),
        "processed_mesh_url": model.get("processed_mesh_url", ""),
        "source_cad_path": model.get("source_cad_path", ""),
        "sidecar_path": model.get("sidecar_path", ""),
        "conversion_report": model.get("conversion_report", ""),
        "preview_path": model.get("preview_path", ""),
        "source_url": model.get("source_url", ""),
        "embed_url": model.get("embed_url", ""),
        "attribution": model.get("attribution", ""),
        "asset_status": model.get("asset_status", ""),
        "license": model.get("license", {}),
        "cad_bridge": cad_bridge,
        "model_maturity": model_maturity,
        "binding_quality": scene_state["binding_quality"],
        "professional_gaps": model_maturity.get("limitations", []),
        "node_bindings": model.get("node_bindings", {}),
        "inspection_views": model.get("inspection_views", []),
        "explode_steps": model.get("explode_steps", []),
        "components": components,
        "highlighted_components": highlighted,
        "hotspots": [
            {**item["hotspot"], "component_key": item["component_key"], "label": item["label"]}
            for item in highlighted
            if item.get("hotspot")
        ],
        "sop_bindings": sop_bindings,
        "safety_gate": safety_gate,
        "scene_state": scene_state,
        "evidence_summary": {
            "manual_hits": len(manual_hits or []),
            "case_hits": len(case_hits or []),
            "has_visual_asset": bool(visual_asset),
            "visual_asset_id": visual_asset.get("id") if visual_asset else None,
            "asset_traceability": model.get("asset_status", ""),
        },
        "reconstruction": {
            "one_photo_available": bool(visual_asset),
            "multi_photo_available": True,
            "default_provider": "cached_demo",
            "decision_policy": "标准 3D 导引用于正式演示；重建结果仅作空间理解，不参与安全放行。",
        },
        "limitations": [
            "3D 模型用于空间理解和 SOP 导引，不代表现场设备真实尺寸。",
            "照片识别与 3D 部件定位必须经过人工复核。",
            "安全闸门以 SOP、手册证据和人工确认为准，不以 3D 重建结果放行。",
        ],
    }
