from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from .database import UPLOAD_DIR
from .spatial_guidance import build_spatial_guidance, ensure_standard_3d_models


PLANNED_BACKENDS = ["COLMAP", "Meshroom", "Nerfstudio Splatfacto"]


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except json.JSONDecodeError:
        return default


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _job_from_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "mode": row["mode"],
        "status": row["status"],
        "equipment": row["equipment"],
        "visual_asset_id": row["visual_asset_id"],
        "input_paths": _json_loads(row["input_paths_json"], []),
        "provider": row["provider"],
        "result_type": row["result_type"],
        "result_path": row["result_path"],
        "preview_path": row["preview_path"],
        "confidence": row["confidence"],
        "limitations": row["limitations"],
        "log": _json_loads(row["log_json"], {}),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_job(conn: sqlite3.Connection, job_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM reconstruction_jobs WHERE id = ?", (job_id,)).fetchone()
    return _job_from_row(row) if row else None


def _insert_job(
    conn: sqlite3.Connection,
    *,
    mode: str,
    status: str,
    equipment: str = "",
    visual_asset_id: int | None = None,
    input_paths: list[str] | None = None,
    provider: str = "cached_demo",
    result_type: str = "",
    result_path: str = "",
    preview_path: str = "",
    confidence: float = 0.0,
    limitations: str = "",
    log: dict | None = None,
) -> dict:
    now = _now()
    cursor = conn.execute(
        """
        INSERT INTO reconstruction_jobs
        (mode, status, equipment, visual_asset_id, input_paths_json, provider,
         result_type, result_path, preview_path, confidence, limitations,
         log_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            mode,
            status,
            equipment,
            visual_asset_id,
            _json_dumps(input_paths or []),
            provider,
            result_type,
            result_path,
            preview_path,
            confidence,
            limitations,
            _json_dumps(log or {}),
            now,
            now,
        ),
    )
    conn.commit()
    return get_job(conn, int(cursor.lastrowid)) or {}


def _visual_equipment(visual_asset: dict | None) -> str:
    if not visual_asset:
        return ""
    candidates = visual_asset.get("analysis", {}).get("equipment_candidates") or [{}]
    return str(visual_asset.get("equipment") or candidates[0].get("id") or "")


def _photo_to_3d_pipeline(*, mode: str, status: str, gate: dict | None = None) -> dict:
    if mode == "one_photo":
        return {
            "algorithm_status": "standard_model_alignment_only",
            "implemented_level": "v0_standard_model_guidance",
            "is_true_3d_generation": False,
            "pipeline_steps": [
                "视觉描述/OCR/缺陷标签提取",
                "设备与部件候选识别",
                "映射到授权标准 CAD/GLB 的 component_key",
                "3D 部件高亮、SOP 绑定和安全闸门展示",
            ],
            "planned_backends": [
                "可选接入 TripoSR / Stable Fast 3D / 3D 生成 API，但只能作为实验性候选网格",
            ],
            "acceptance_criteria": [
                "能稳定定位到标准模型部件",
                "必须展示证据、SOP 和安全限制",
                "不得用于尺寸测量或安全放行",
            ],
        }
    return {
        "algorithm_status": status,
        "implemented_level": "v0_quality_gate_offline_package",
        "is_true_3d_generation": False,
        "quality_gate": gate or {},
        "pipeline_steps": [
            "同一设备多角度照片采集",
            "照片数量、格式和重复视角质量门",
            "生成离线重建任务包",
            "COLMAP/Meshroom/Nerfstudio 离线执行",
            "人工验收后再写入 3D sidecar 和证据链",
        ],
        "planned_backends": PLANNED_BACKENDS,
        "acceptance_criteria": [
            "建议至少 12 张照片且覆盖关键视角",
            "输出模型必须可打开且不是空模型",
            "关键部件必须人工标注到 component_key",
            "未经计量校准不得用于尺寸测量或安全放行",
        ],
    }


def create_one_photo_job(conn: sqlite3.Connection, visual_asset: dict, provider: str = "cached_demo") -> dict:
    ensure_standard_3d_models(conn)
    equipment = _visual_equipment(visual_asset) or "general"
    stable_provider = provider in {"", "cached_demo", "disabled"}
    guidance = build_spatial_guidance(
        conn,
        equipment=equipment if equipment != "general" else "motor",
        model_code="",
        text=visual_asset.get("caption", ""),
        visual_asset=visual_asset,
        sop={"sop_steps": [], "compliance": []},
        manual_hits=[],
        case_hits=[],
    )
    pipeline = _photo_to_3d_pipeline(mode="one_photo", status="standard_model_alignment_only")
    return _insert_job(
        conn,
        mode="one_photo",
        status="completed_cached" if stable_provider else "queued",
        equipment=equipment,
        visual_asset_id=int(visual_asset["id"]),
        input_paths=[visual_asset.get("stored_path", "")],
        provider=provider or "cached_demo",
        result_type="standard_model_guidance" if stable_provider else "pending_external_generation",
        result_path=guidance["mesh_path"],
        confidence=0.62,
        limitations="单图当前只做照片语义到标准 3D 模型的部件定位，不生成新的 mesh；结果仅用于空间理解，不作为尺寸测量或安全放行依据。",
        log={
            "policy": "stable_demo_first",
            "guidance_model_id": guidance["model_id"],
            "highlighted_components": guidance["highlighted_components"],
            **pipeline,
        },
    )


def _quality_gate(files: list[UploadFile]) -> dict:
    names = [Path(file.filename or "photo").name for file in files]
    image_like = [name for name in names if Path(name).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
    unique_count = len(set(names))
    issues: list[str] = []
    if len(files) < 12:
        issues.append("多图重建建议至少 12 张同一设备不同角度照片")
    if len(image_like) != len(files):
        issues.append("仅接受 jpg/jpeg/png/webp 图片")
    if unique_count < len(files):
        issues.append("存在重复文件名，需要补充不同视角")
    score = 1.0
    score -= max(0, 12 - len(files)) * 0.055
    if issues:
        score -= 0.18 * len(issues)
    return {
        "passed": not issues,
        "score": round(max(0.0, min(score, 1.0)), 2),
        "issues": issues,
        "photo_count": len(files),
        "unique_count": unique_count,
    }


async def create_multi_photo_job(
    conn: sqlite3.Connection,
    *,
    files: list[UploadFile],
    equipment: str = "",
    provider: str = "offline_package",
) -> dict:
    ensure_standard_3d_models(conn)
    gate = _quality_gate(files)
    target_dir = UPLOAD_DIR / "3d" / datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    target_dir.mkdir(parents=True, exist_ok=True)
    input_paths: list[str] = []
    for index, file in enumerate(files, start=1):
        safe_name = Path(file.filename or f"photo-{index}.jpg").name
        target = target_dir / f"{index:02d}-{safe_name}"
        with target.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
        input_paths.append(str(target))

    status = "ready_for_offline_reconstruction" if gate["passed"] else "blocked_quality_gate"
    result_type = "colmap_meshroom_nerfstudio_task_package" if gate["passed"] else "quality_gate_report"
    runner_command = f'python scripts/run_3d_reconstruction.py --job-id <id> --input-dir "{target_dir}"'
    pipeline = _photo_to_3d_pipeline(mode="multi_photo", status=status, gate=gate)
    return _insert_job(
        conn,
        mode="multi_photo",
        status=status,
        equipment=equipment,
        input_paths=input_paths,
        provider=provider or "offline_package",
        result_type=result_type,
        result_path=str(target_dir),
        confidence=gate["score"],
        limitations="多图当前只生成离线重建任务包；真实 3D 需要 COLMAP/Meshroom/Nerfstudio 执行和人工验收，未验收前不作为尺寸测量或安全放行依据。",
        log={
            **pipeline,
            "next_command": runner_command,
            "runner_command": runner_command,
            "supported_backends": PLANNED_BACKENDS,
        },
    )
