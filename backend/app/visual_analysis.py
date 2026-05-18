from __future__ import annotations

import json
import mimetypes
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .model_gateway import analyze_image_file


def _candidate(identifier: str, label: str, confidence: float) -> dict[str, Any]:
    return {"id": identifier, "label": label, "confidence": confidence}


def _label(label: str, confidence: float) -> dict[str, Any]:
    return {"label": label, "confidence": confidence}


def rule_based_visual_analysis(filename: str, fallback_caption: str = "") -> dict[str, Any]:
    text = filename.lower()
    if any(word in text for word in ["bearing", "spall", "wear", "roller", "brinelling", "fretting", "轴承", "剥落", "磨损"]):
        return {
            "caption": fallback_caption or "图片疑似显示轴承滚道剥落、磨损、压痕或润滑异常，需要检查游隙、滚道、保持架和润滑状态。",
            "equipment_candidates": [_candidate("bearing", "轴承", 0.88)],
            "component_candidates": [_label("滚道", 0.82), _label("保持架", 0.68), _label("外圈", 0.64)],
            "defect_labels": [_label("轴承剥落/磨损", 0.86), _label("润滑异常", 0.72)],
            "ocr_text": "",
            "flowchart": {"nodes": [], "edges": [], "summary": ""},
            "risk_hints": ["拆装区域保持清洁", "禁止硬敲滚道", "佩戴护目镜和防割手套"],
            "retrieval_keywords": ["轴承", "剥落", "磨损", "压痕", "润滑", "游隙", "保持架"],
        }
    if any(word in text for word in ["pump", "seal", "leak", "impeller", "cavitation", "erosion", "泵", "泄漏", "密封", "汽蚀"]):
        return {
            "caption": fallback_caption or "图片疑似显示离心泵密封、叶轮、泵壳或泄漏痕迹，需要检查机械密封、入口条件、压力流量和介质残余能量。",
            "equipment_candidates": [_candidate("pump", "离心泵", 0.86)],
            "component_candidates": [_label("机械密封", 0.84), _label("叶轮", 0.72), _label("泵体", 0.7)],
            "defect_labels": [_label("泵泄漏/密封异常", 0.86), _label("汽蚀/腐蚀风险", 0.62)],
            "ocr_text": "",
            "flowchart": {"nodes": [], "edges": [], "summary": ""},
            "risk_hints": ["隔离介质", "泄压排液", "设置防滑警示"],
            "retrieval_keywords": ["离心泵", "机械密封", "泄漏", "O形圈", "叶轮", "汽蚀", "泄压", "排液"],
        }
    if any(word in text for word in ["motor", "stator", "rotor", "hot", "burnt", "电机", "端盖"]):
        return {
            "caption": fallback_caption or "图片疑似显示电机端盖、轴承座、转子或绕组区域异常，需要结合温升、振动和绝缘数据复核。",
            "equipment_candidates": [_candidate("motor", "电机", 0.84)],
            "component_candidates": [_label("端盖", 0.76), _label("轴承座", 0.7), _label("转子/绕组", 0.62)],
            "defect_labels": [_label("电机过热/损伤", 0.74), _label("轴承异常", 0.7)],
            "ocr_text": "",
            "flowchart": {"nodes": [], "edges": [], "summary": ""},
            "risk_hints": ["停机断电挂牌", "绝缘测试", "空载试运行"],
            "retrieval_keywords": ["电机", "端盖", "过热", "振动", "绝缘", "轴承", "转子"],
        }
    if any(word in text for word in ["engine", "spark", "plug", "cylinder", "发动机", "火花塞"]):
        return {
            "caption": fallback_caption or "图片疑似显示发动机火花塞、气缸或起动相关部件，需要复核火花塞间隙和压缩压力。",
            "equipment_candidates": [_candidate("engine", "发动机", 0.84)],
            "component_candidates": [_label("火花塞", 0.82), _label("气缸头", 0.64)],
            "defect_labels": [_label("火花塞积碳/间隙异常", 0.78), _label("压缩压力相关", 0.6)],
            "ocr_text": "",
            "flowchart": {"nodes": [], "edges": [], "summary": ""},
            "risk_hints": ["冷机拆装", "断开点火或喷油连接", "防止误启动"],
            "retrieval_keywords": ["发动机", "火花塞", "间隙", "压缩压力", "气缸", "误启动"],
        }
    return {
        "caption": fallback_caption or "图片已接收，未识别到明确设备类别，按通用设备异常参与检索。",
        "equipment_candidates": [_candidate("general", "通用设备", 0.52)],
        "component_candidates": [_label("待确认部件", 0.5)],
        "defect_labels": [_label("未知异常", 0.5)],
        "ocr_text": "",
        "flowchart": {"nodes": [], "edges": [], "summary": ""},
        "risk_hints": ["补充设备型号", "人工复核图片语义", "保留现场照片"],
        "retrieval_keywords": ["设备异常", "检修", "图片", "人工复核"],
    }


def normalize_visual_analysis(payload: dict[str, Any], fallback_caption: str = "") -> dict[str, Any]:
    base = rule_based_visual_analysis("", fallback_caption)
    merged = {**base, **(payload or {})}
    merged["caption"] = str(merged.get("caption") or fallback_caption or base["caption"])
    for field in ["equipment_candidates", "component_candidates", "defect_labels", "risk_hints", "retrieval_keywords"]:
        value = merged.get(field)
        merged[field] = value if isinstance(value, list) else []
    flowchart = merged.get("flowchart")
    if not isinstance(flowchart, dict):
        flowchart = {"nodes": [], "edges": [], "summary": ""}
    flowchart.setdefault("nodes", [])
    flowchart.setdefault("edges", [])
    flowchart.setdefault("summary", "")
    merged["flowchart"] = flowchart
    merged["ocr_text"] = str(merged.get("ocr_text") or "")
    merged["ok"] = bool(merged.get("ok", True))
    merged["provider"] = str(merged.get("provider") or "local")
    merged["model"] = str(merged.get("model") or "")
    merged["error"] = str(merged.get("error") or "")
    return merged


def analyze_visual_file(path: Path, filename: str, fallback_caption: str = "") -> dict[str, Any]:
    fallback = rule_based_visual_analysis(filename, fallback_caption)
    analysis = analyze_image_file(str(path), fallback)
    return normalize_visual_analysis(analysis, fallback_caption=fallback["caption"])


def _first_label(items: list[dict[str, Any]], default: str = "") -> str:
    if not items:
        return default
    return str(items[0].get("label") or items[0].get("id") or default)


def _first_equipment(items: list[dict[str, Any]], default: str = "") -> str:
    if not items:
        return default
    return str(items[0].get("id") or default)


def save_visual_asset(
    conn: sqlite3.Connection,
    *,
    filename: str,
    stored_path: str,
    analysis: dict[str, Any],
    manifest_id: str = "",
    source_url: str = "",
    source_note: str = "",
    license_note: str = "",
    review_status: str = "unreviewed",
    reviewer: str = "",
    sha256: str = "",
    width: int = 0,
    height: int = 0,
) -> int:
    normalized = normalize_visual_analysis(analysis)
    now = datetime.utcnow().isoformat(timespec="seconds")
    cursor = conn.execute(
        """
        INSERT INTO visual_assets
        (filename, stored_path, mime_type, caption, equipment, component, defect_labels,
         ocr_text, flowchart_json, analysis_json, provider, model, ok, manifest_id,
         source_url, source_note, license_note, review_status, reviewer, sha256,
         width, height, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            filename,
            stored_path,
            mimetypes.guess_type(filename)[0] or "",
            normalized["caption"],
            _first_equipment(normalized["equipment_candidates"]),
            _first_label(normalized["component_candidates"]),
            json.dumps(normalized["defect_labels"], ensure_ascii=False),
            normalized["ocr_text"],
            json.dumps(normalized["flowchart"], ensure_ascii=False),
            json.dumps(normalized, ensure_ascii=False),
            normalized["provider"],
            normalized["model"],
            1 if normalized["ok"] else 0,
            manifest_id,
            source_url,
            source_note,
            license_note,
            review_status,
            reviewer,
            sha256,
            int(width or 0),
            int(height or 0),
            now,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _row_to_visual_asset(row: sqlite3.Row) -> dict[str, Any]:
    analysis = normalize_visual_analysis(json.loads(row["analysis_json"] or "{}"), row["caption"])
    analysis["id"] = row["id"]
    return {
        "id": row["id"],
        "filename": row["filename"],
        "stored_path": row["stored_path"],
        "mime_type": row["mime_type"],
        "caption": row["caption"],
        "equipment": row["equipment"],
        "component": row["component"],
        "defect_labels": json.loads(row["defect_labels"] or "[]"),
        "ocr_text": row["ocr_text"],
        "flowchart": json.loads(row["flowchart_json"] or "{}"),
        "provider": row["provider"],
        "model": row["model"],
        "ok": bool(row["ok"]),
        "manifest_id": row["manifest_id"] if "manifest_id" in row.keys() else "",
        "source_url": row["source_url"] if "source_url" in row.keys() else "",
        "source_note": row["source_note"] if "source_note" in row.keys() else "",
        "license_note": row["license_note"] if "license_note" in row.keys() else "",
        "review_status": row["review_status"] if "review_status" in row.keys() else "",
        "reviewer": row["reviewer"] if "reviewer" in row.keys() else "",
        "sha256": row["sha256"] if "sha256" in row.keys() else "",
        "width": row["width"] if "width" in row.keys() else 0,
        "height": row["height"] if "height" in row.keys() else 0,
        "created_at": row["created_at"],
        "analysis": analysis,
    }


def load_visual_asset(conn: sqlite3.Connection, asset_id: int | None) -> dict[str, Any] | None:
    if not asset_id:
        return None
    row = conn.execute("SELECT * FROM visual_assets WHERE id = ?", (asset_id,)).fetchone()
    return _row_to_visual_asset(row) if row else None


def list_visual_assets(conn: sqlite3.Connection, limit: int = 40) -> list[dict[str, Any]]:
    safe_limit = min(max(limit, 1), 200)
    rows = conn.execute(
        "SELECT * FROM visual_assets ORDER BY id DESC LIMIT ?",
        (safe_limit,),
    ).fetchall()
    return [_row_to_visual_asset(row) for row in rows]


def visual_query_text(asset: dict[str, Any] | None) -> str:
    if not asset:
        return ""
    analysis = asset.get("analysis", {})
    defect_labels = [str(item.get("label", "")) for item in analysis.get("defect_labels", []) if item.get("label")]
    components = [str(item.get("label", "")) for item in analysis.get("component_candidates", []) if item.get("label")]
    keywords = [str(item) for item in analysis.get("retrieval_keywords", []) if item]
    return " ".join(
        [
            analysis.get("caption", ""),
            analysis.get("ocr_text", ""),
            " ".join(defect_labels),
            " ".join(components),
            " ".join(keywords),
        ]
    ).strip()
