from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .database import PROJECT_ROOT
from .retrieval import EQUIPMENT_LABELS
from .visual_analysis import normalize_visual_analysis, rule_based_visual_analysis

MANIFEST_PATH = PROJECT_ROOT / "data" / "image_eval" / "fault_image_eval_manifest.csv"
REQUIRED_VISUAL_ASSETS = 30


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return image.width, image.height
    except Exception:  # noqa: BLE001
        return 0, 0


def _split_keywords(value: str) -> list[str]:
    return [item.strip() for item in (value or "").replace("，", " ").replace(",", " ").split() if item.strip()]


def _candidate(identifier: str, confidence: float = 0.9) -> dict[str, Any]:
    return {
        "id": identifier,
        "label": EQUIPMENT_LABELS.get(identifier, identifier),
        "confidence": confidence,
    }


def _label(label: str, confidence: float = 0.82) -> dict[str, Any]:
    return {"label": label, "confidence": confidence}


def _component_labels(row: dict[str, str]) -> list[dict[str, Any]]:
    text = " ".join(
        [
            row.get("fault_type", ""),
            row.get("visible_evidence", ""),
            row.get("caption_hint", ""),
            row.get("expected_retrieval_keywords", ""),
        ]
    )
    equipment = row.get("equipment", "")
    if equipment == "motor":
        candidates = [
            ("轴承", ["轴承", "bearing"]),
            ("端盖/轴承座", ["端盖", "轴承座", "bottom cup"]),
            ("转子", ["转子", "rotor"]),
            ("定子/绕组", ["定子", "绕组", "stator", "burnt"]),
            ("密封件", ["密封", "grease seal"]),
        ]
    elif equipment == "pump":
        candidates = [
            ("机械密封", ["机械密封", "密封", "seal", "gland", "packing"]),
            ("叶轮", ["叶轮", "impeller", "cavitation"]),
            ("泵壳", ["泵壳", "泵体", "corrosion", "erosion"]),
            ("入口过滤/管路", ["入口", "过滤", "流量", "pressure"]),
            ("轴承箱", ["轴承箱", "bearing"]),
        ]
    elif equipment == "bearing":
        candidates = [
            ("滚道", ["滚道", "剥落", "spall", "damage"]),
            ("外圈", ["外圈", "outer"]),
            ("保持架", ["保持架", "cage"]),
            ("滚动体", ["滚动体", "roller", "ball"]),
            ("润滑脂", ["润滑", "grease", "fretting"]),
        ]
    else:
        candidates = [
            ("火花塞", ["火花塞", "spark"]),
            ("气缸头", ["气缸", "cylinder"]),
            ("起动系统", ["起动", "starter"]),
        ]
    matched = [_label(label) for label, keys in candidates if any(key.lower() in text.lower() for key in keys)]
    return matched[:3] or [_label("待确认部件", 0.55)]


def _defect_labels(row: dict[str, str]) -> list[dict[str, Any]]:
    fault = (row.get("fault_type") or "visual_fault").replace("_", " ")
    visible = row.get("visible_evidence", "")
    if row.get("equipment") == "pump" and "cavitation" in fault:
        return [_label("叶轮汽蚀/点蚀", 0.88), _label("流量压力异常", 0.76)]
    if row.get("equipment") == "pump" and any(word in fault for word in ["seal", "leak", "packing"]):
        return [_label("机械密封/填料泄漏", 0.88), _label("端面或 O 形圈异常", 0.74)]
    if row.get("equipment") == "motor" and any(word in fault for word in ["overheat", "burnt"]):
        return [_label("电机过热/烧损", 0.88), _label("绝缘或通风异常", 0.72)]
    if row.get("equipment") == "motor" and "rotor" in fault:
        return [_label("转子损伤/擦碰", 0.84), _label("轴承间隙异常风险", 0.7)]
    if row.get("equipment") == "bearing":
        if any(word in fault for word in ["brinelling", "fretting"]):
            return [_label("压痕/微动磨损", 0.86), _label("润滑污染或振动冲击", 0.74)]
        return [_label("轴承损伤/滚道异常", 0.86), _label("润滑或装配异常", 0.74)]
    label = visible.split("；", 1)[0].strip() or fault
    return [_label(label[:24], 0.78)]


def analysis_from_manifest_row(row: dict[str, str], *, width: int = 0, height: int = 0) -> dict[str, Any]:
    image_path = row.get("image_path", "")
    base = rule_based_visual_analysis(image_path, row.get("caption_hint", ""))
    equipment = row.get("equipment", "") or "general"
    keywords = _split_keywords(row.get("expected_retrieval_keywords", ""))
    safety = _split_keywords(row.get("expected_safety_keywords", ""))
    source = row.get("source_note", "")
    payload = {
        **base,
        "caption": row.get("caption_hint") or base["caption"],
        "equipment_candidates": [_candidate(equipment)],
        "component_candidates": _component_labels(row),
        "defect_labels": _defect_labels(row),
        "ocr_text": "",
        "flowchart": {
            "nodes": [],
            "edges": [],
            "summary": "该图片不是流程图；已按设备、部件、缺陷标签和人工审核语义进入检索。",
        },
        "ocr_status": "not_applicable_or_no_visible_text",
        "risk_hints": safety or base.get("risk_hints", []),
        "retrieval_keywords": list(dict.fromkeys([*keywords, equipment, row.get("fault_type", "")])),
        "source_page": source,
        "license_note": row.get("license_note", ""),
        "review": {
            "status": row.get("review_status", ""),
            "reviewer": row.get("reviewer", ""),
            "notes": row.get("review_notes", ""),
        },
        "image_meta": {"width": width, "height": height},
        "ok": True,
        "provider": "cached_manifest",
        "model": "mechanical-review-v1",
        "error": "",
    }
    return normalize_visual_analysis(payload, fallback_caption=payload["caption"])


def _read_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _upsert_visual_asset(conn: sqlite3.Connection, row: dict[str, str]) -> dict[str, Any]:
    image_path = PROJECT_ROOT / row["image_path"]
    width, height = _image_size(image_path)
    sha = _sha256(image_path)
    analysis = analysis_from_manifest_row(row, width=width, height=height)
    now = datetime.utcnow().isoformat(timespec="seconds")
    filename = image_path.name
    stored_path = str(image_path)
    manifest_id = row["id"]
    existing = conn.execute(
        """
        SELECT id FROM visual_assets
        WHERE manifest_id = ?
           OR (manifest_id = '' AND filename = ?)
        ORDER BY id
        LIMIT 1
        """,
        (manifest_id, filename),
    ).fetchone()
    values = (
        filename,
        stored_path,
        analysis["caption"],
        analysis["equipment_candidates"][0]["id"],
        analysis["component_candidates"][0]["label"],
        json.dumps(analysis["defect_labels"], ensure_ascii=False),
        analysis["ocr_text"],
        json.dumps(analysis["flowchart"], ensure_ascii=False),
        json.dumps(analysis, ensure_ascii=False),
        analysis["provider"],
        analysis["model"],
        1,
        manifest_id,
        row.get("source_note", ""),
        row.get("source_note", ""),
        row.get("license_note", ""),
        row.get("review_status", ""),
        row.get("reviewer", ""),
        sha,
        width,
        height,
        now,
    )
    if existing:
        conn.execute(
            """
            UPDATE visual_assets
            SET filename = ?, stored_path = ?, mime_type = 'image/*', caption = ?,
                equipment = ?, component = ?, defect_labels = ?, ocr_text = ?,
                flowchart_json = ?, analysis_json = ?, provider = ?, model = ?, ok = ?,
                manifest_id = ?, source_url = ?, source_note = ?, license_note = ?,
                review_status = ?, reviewer = ?, sha256 = ?, width = ?, height = ?,
                created_at = ?
            WHERE id = ?
            """,
            (*values, existing["id"]),
        )
        return {"id": existing["id"], "action": "updated", "manifest_id": manifest_id}
    cursor = conn.execute(
        """
        INSERT INTO visual_assets
        (filename, stored_path, mime_type, caption, equipment, component, defect_labels,
         ocr_text, flowchart_json, analysis_json, provider, model, ok, manifest_id,
         source_url, source_note, license_note, review_status, reviewer, sha256,
         width, height, created_at)
        VALUES (?, ?, 'image/*', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        values,
    )
    return {"id": cursor.lastrowid, "action": "inserted", "manifest_id": manifest_id}


def ensure_image_eval_visual_assets(
    conn: sqlite3.Connection,
    *,
    manifest_path: Path = MANIFEST_PATH,
    required: int = REQUIRED_VISUAL_ASSETS,
) -> dict[str, Any]:
    rows = _read_manifest(manifest_path)
    inserted = 0
    updated = 0
    skipped: list[dict[str, str]] = []
    for row in rows:
        if (row.get("review_status") or "").strip().lower() != "approved":
            skipped.append({"id": row.get("id", ""), "reason": "not_approved"})
            continue
        image_path = PROJECT_ROOT / (row.get("image_path") or "")
        if not image_path.exists():
            skipped.append({"id": row.get("id", ""), "reason": "missing_image"})
            continue
        result = _upsert_visual_asset(conn, row)
        inserted += int(result["action"] == "inserted")
        updated += int(result["action"] == "updated")
    conn.commit()
    approved_count = conn.execute(
        "SELECT COUNT(*) AS c FROM visual_assets WHERE review_status = 'approved'"
    ).fetchone()["c"]
    available_count = conn.execute("SELECT COUNT(*) AS c FROM visual_assets").fetchone()["c"]
    return {
        "manifest": str(manifest_path),
        "manifest_rows": len(rows),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "available_visual_assets": available_count,
        "approved_visual_assets": approved_count,
        "ready": approved_count >= required,
    }
