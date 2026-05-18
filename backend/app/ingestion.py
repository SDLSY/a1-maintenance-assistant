from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from .vector_index import rebuild_embeddings

RAW_MANUAL_DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "manuals"


def guess_equipment(text: str, filename: str) -> str:
    haystack = f"{filename} {text[:1000]}".lower()
    if any(word in haystack for word in ["pump", "泵", "离心"]):
        return "pump"
    if any(word in haystack for word in ["bearing", "轴承", "6205"]):
        return "bearing"
    if any(word in haystack for word in ["engine", "发动机", "火花塞", "气缸", "压缩压力"]):
        return "engine"
    if any(word in haystack for word in ["motor", "电机", "异步"]):
        return "motor"
    return "general"


def guess_fault(text: str) -> str:
    if any(word in text for word in ["泄漏", "滴漏", "密封"]):
        return "泄漏"
    if any(word in text for word in ["汽蚀", "流量", "压力波动"]):
        return "汽蚀/流量不足"
    if any(word in text for word in ["温升", "过热", "发热"]):
        return "过热"
    if any(word in text for word in ["振动", "异响", "噪声"]):
        return "振动/异响"
    if any(word in text for word in ["绝缘", "绕组"]):
        return "绝缘下降"
    if any(word in text for word in ["火花塞", "点火", "间隙"]):
        return "火花塞检查"
    if any(word in text for word in ["压缩压力", "气缸压力"]):
        return "压缩压力异常"
    if any(word in text for word in ["水泵", "机油泵"]):
        return "泵系检查"
    if any(word in text for word in ["剥落", "磨损", "保持架"]):
        return "磨损/剥落"
    return "通用检修"


def guess_component(text: str) -> str:
    for component in ["火花塞", "起动电机", "发动机", "气缸头", "气门", "活塞", "机油泵", "水泵", "离合器", "传动装置", "曲轴", "轴承", "机械密封", "叶轮", "联轴器", "绕组", "端盖", "泵轴", "安全"]:
        if component in text:
            return component
    return "设备"


def extract_text_pages(path: Path) -> list[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF 入库需要安装 pypdf：pip install pypdf") from exc
        reader = PdfReader(str(path))
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            pages.append((index, page.extract_text() or ""))
        return pages
    return []


def chunk_page(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|(?<=。)", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) <= max_chars:
            current = f"{current}\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            current = (current[-overlap:] + "\n" + paragraph).strip() if overlap else paragraph
    if current:
        chunks.append(current[:max_chars])
    return chunks


def ingest_file(
    conn: sqlite3.Connection,
    path: Path,
    *,
    source_url: str = "",
    license_name: str = "unknown",
    version: str = "",
    equipment_override: str = "",
    rebuild: bool = True,
) -> dict:
    existing = conn.execute("SELECT id FROM documents WHERE path = ?", (str(path),)).fetchone()
    if existing:
        equipment = equipment_override or ""
        if source_url or license_name != "unknown" or version or equipment:
            conn.execute(
                """
                UPDATE documents
                SET source_url = COALESCE(NULLIF(?, ''), source_url),
                    license = ?,
                    version = COALESCE(NULLIF(?, ''), version),
                    equipment = COALESCE(NULLIF(?, ''), equipment)
                WHERE id = ?
                """,
                (source_url, license_name, version, equipment, existing["id"]),
            )
            conn.execute(
                """
                UPDATE manual_chunks
                SET source_url = COALESCE(NULLIF(?, ''), source_url),
                    license = ?,
                    version = COALESCE(NULLIF(?, ''), version),
                    equipment = COALESCE(NULLIF(?, ''), equipment)
                WHERE doc_id = ?
                """,
                (source_url, license_name, version, equipment, existing["id"]),
            )
            conn.commit()
        return {
            "document_id": existing["id"],
            "chunks": 0,
            "equipment": equipment or "existing",
            "status": "exists",
        }

    pages = extract_text_pages(path)
    full_text = "\n".join(page_text for _, page_text in pages)
    equipment = equipment_override or guess_equipment(full_text, path.name)
    now = datetime.utcnow().isoformat(timespec="seconds")
    cursor = conn.execute(
        """
        INSERT INTO documents
        (title, path, source_url, license, version, equipment, model, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (path.stem, str(path), source_url, license_name, version, equipment, "", now),
    )
    doc_id = cursor.lastrowid
    inserted = 0
    for page, page_text in pages:
        for index, chunk in enumerate(chunk_page(page_text), start=1):
            if len(chunk) < 30:
                continue
            conn.execute(
                """
                INSERT INTO manual_chunks
                (doc_id, title, equipment, model, source, page, section, component,
                 fault_type, maintenance_level, modality, content, image_caption,
                 license, version, source_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    path.stem,
                    equipment,
                    "",
                    path.name,
                    page,
                    f"自动入库片段 {page}-{index}",
                    guess_component(chunk),
                    guess_fault(chunk),
                    "二级检修",
                    "text",
                    chunk,
                    "",
                    license_name,
                    version,
                    source_url,
                    now,
                ),
            )
            inserted += 1
    conn.commit()
    if rebuild:
        rebuild_embeddings(conn)
    return {"document_id": doc_id, "chunks": inserted, "equipment": equipment, "status": "ingested"}


def source_metadata_for(path: Path) -> dict:
    sidecar = path.with_name(f"{path.name}.source.json")
    if not sidecar.exists():
        return {}
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def ingest_directory(
    conn: sqlite3.Connection,
    directory: Path = RAW_MANUAL_DIR,
    *,
    rebuild: bool = True,
) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    results = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".txt", ".md", ".pdf"}:
            metadata = source_metadata_for(path)
            results.append(
                ingest_file(
                    conn,
                    path,
                    source_url=metadata.get("source_url", ""),
                    license_name=metadata.get("license", "unknown"),
                    version=metadata.get("version", ""),
                    equipment_override=metadata.get("equipment", ""),
                    rebuild=False,
                )
            )
    rebuild_result = rebuild_embeddings(conn) if results and rebuild else {"skipped": not rebuild}
    return {
        "directory": str(directory),
        "documents": results,
        "count": len(results),
        "index": rebuild_result,
    }
