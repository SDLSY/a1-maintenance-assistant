from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from fastapi import HTTPException


def promote_candidate_to_model(
    conn: sqlite3.Connection,
    candidate: dict[str, Any],
    *,
    model_title: str,
    component_binding_mode: str = "candidate_component_key",
) -> dict[str, Any]:
    if candidate.get("status") != "approved_candidate":
        raise HTTPException(status_code=400, detail="candidate must be approved before promotion")
    manifest = candidate.get("artifact_manifest") or {}
    glb_path = ((manifest.get("cad_files") or {}).get("glb") or {}).get("path", "")
    if not glb_path:
        raise HTTPException(status_code=400, detail="candidate has no GLB artifact")
    model_id = f"candidate-cad-{int(candidate['id']):04d}"
    model_code = candidate.get("model", "")
    equipment = candidate.get("equipment", "general")
    spec = candidate.get("editable_spec") or candidate.get("cad_spec") or {}
    component_keys = spec.get("component_keys") or []
    now = datetime.utcnow().isoformat(timespec="seconds")
    node_bindings = {
        "binding_mode": component_binding_mode,
        "semantic_sidecar_ready": True,
        "exact_cad_face_binding": False,
        "candidate_cad_asset_id": candidate["id"],
        "component_keys": component_keys,
        "not_for_measurement": True,
    }
    conn.execute(
        """
        INSERT INTO standard_3d_models
        (id, equipment, model_code, title, source_type, mesh_path, processed_mesh_path,
         processed_mesh_url, source_cad_path, viewer_mode, asset_status, license_json,
         node_bindings_json, created_at)
        VALUES (?, ?, ?, ?, 'candidate_cad', ?, ?, ?, ?, 'local_glb', 'candidate_reviewed', ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          title=excluded.title,
          mesh_path=excluded.mesh_path,
          processed_mesh_path=excluded.processed_mesh_path,
          processed_mesh_url=excluded.processed_mesh_url,
          source_cad_path=excluded.source_cad_path,
          node_bindings_json=excluded.node_bindings_json,
          asset_status=excluded.asset_status
        """,
        (
            model_id,
            equipment,
            model_code,
            model_title,
            f"/api/cad/candidates/{candidate['id']}/files/glb",
            glb_path,
            f"/api/cad/candidates/{candidate['id']}/files/glb",
            ((manifest.get("cad_files") or {}).get("step") or {}).get("path", ""),
            json.dumps({"id": "candidate-review", "name": "Reviewed candidate asset"}, ensure_ascii=False),
            json.dumps(node_bindings, ensure_ascii=False),
            now,
        ),
    )
    for index, component_key in enumerate(component_keys):
        local_key = str(component_key).split(".", 1)[-1]
        label = local_key.replace("_", " ")
        conn.execute(
            """
            INSERT INTO model_components
            (model_id, component_key, label, geometry_json, hotspot_json,
             fault_tags, safety_tags, manual_keywords)
            VALUES (?, ?, ?, '{}', ?, '[]', '[]', '[]')
            ON CONFLICT(model_id, component_key) DO UPDATE SET
              label=excluded.label,
              hotspot_json=excluded.hotspot_json
            """,
            (
                model_id,
                local_key,
                label,
                json.dumps({"x": 0.1 * index, "y": 0.1, "z": 0.05, "source": "candidate_cad"}, ensure_ascii=False),
            ),
        )
    return {
        "status": "promoted_standard_candidate",
        "model_id": model_id,
        "viewer_mode": "local_glb",
        "candidate_id": candidate["id"],
    }
