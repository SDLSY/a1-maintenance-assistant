from __future__ import annotations

import sqlite3
import csv
import os
from datetime import datetime
from pathlib import Path

from .seed_data import CASES, EVAL_QUESTIONS, KG_EDGES, KG_NODES, MANUAL_CHUNKS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = Path(os.getenv("A1_DB_PATH", str(DATA_DIR / "maintenance.db")))


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            path TEXT NOT NULL,
            source_url TEXT DEFAULT '',
            license TEXT DEFAULT 'unknown',
            version TEXT DEFAULT '',
            equipment TEXT NOT NULL,
            model TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS manual_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER,
            title TEXT NOT NULL,
            equipment TEXT NOT NULL,
            model TEXT NOT NULL,
            source TEXT NOT NULL,
            page INTEGER NOT NULL,
            section TEXT NOT NULL,
            component TEXT NOT NULL,
            fault_type TEXT NOT NULL,
            maintenance_level TEXT NOT NULL,
            modality TEXT NOT NULL,
            content TEXT NOT NULL,
            image_caption TEXT DEFAULT '',
            license TEXT DEFAULT 'unknown',
            version TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS maintenance_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            equipment TEXT NOT NULL,
            model TEXT NOT NULL,
            symptoms TEXT NOT NULL,
            fault_type TEXT NOT NULL,
            cause TEXT NOT NULL,
            actions TEXT NOT NULL,
            parts TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS kg_nodes (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            type TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS kg_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            relation TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            original_answer TEXT NOT NULL,
            corrected_answer TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunk_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            model TEXT NOT NULL,
            dim INTEGER NOT NULL,
            vector_json TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(source_type, source_id, model)
        );

        CREATE TABLE IF NOT EXISTS eval_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            equipment TEXT NOT NULL,
            model TEXT DEFAULT '',
            expected_source_ids TEXT NOT NULL,
            expected_fault_type TEXT NOT NULL,
            expected_safety_keywords TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS eval_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            recall_at_5 REAL NOT NULL,
            citation_coverage REAL NOT NULL,
            sop_score REAL NOT NULL,
            hallucination_rate REAL NOT NULL,
            safety_miss_rate REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    _ensure_column(conn, "manual_chunks", "doc_id", "INTEGER")
    _ensure_column(conn, "manual_chunks", "license", "TEXT DEFAULT 'unknown'")
    _ensure_column(conn, "manual_chunks", "version", "TEXT DEFAULT ''")
    _ensure_column(conn, "manual_chunks", "source_url", "TEXT DEFAULT ''")
    _ensure_column(conn, "manual_chunks", "created_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "maintenance_cases", "review_status", "TEXT DEFAULT 'unreviewed'")
    _ensure_column(conn, "maintenance_cases", "reviewer", "TEXT DEFAULT ''")
    _ensure_column(conn, "maintenance_cases", "review_notes", "TEXT DEFAULT ''")
    _ensure_column(conn, "eval_questions", "review_status", "TEXT DEFAULT 'unreviewed'")
    _ensure_column(conn, "eval_questions", "reviewer", "TEXT DEFAULT ''")
    _ensure_column(conn, "eval_questions", "review_notes", "TEXT DEFAULT ''")
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def seed_if_empty(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) AS c FROM manual_chunks").fetchone()["c"]
    if not count:
        conn.executemany(
            """
            INSERT INTO manual_chunks
            (title, equipment, model, source, page, section, component, fault_type,
             maintenance_level, modality, content, image_caption)
            VALUES
            (:title, :equipment, :model, :source, :page, :section, :component,
             :fault_type, :maintenance_level, :modality, :content, :image_caption)
            """,
            MANUAL_CHUNKS,
        )

    now = datetime.utcnow().isoformat(timespec="seconds")
    case_count = conn.execute("SELECT COUNT(*) AS c FROM maintenance_cases").fetchone()["c"]
    if not case_count:
        conn.executemany(
            """
            INSERT INTO maintenance_cases
            (title, equipment, model, symptoms, fault_type, cause, actions, parts,
             risk_level, status, created_at)
            VALUES
            (:title, :equipment, :model, :symptoms, :fault_type, :cause, :actions,
             :parts, :risk_level, :status, :created_at)
            """,
            [{**case, "created_at": now} for case in CASES],
        )

    kg_count = conn.execute("SELECT COUNT(*) AS c FROM kg_nodes").fetchone()["c"]
    if not kg_count:
        conn.executemany("INSERT INTO kg_nodes (id, label, type) VALUES (?, ?, ?)", KG_NODES)
        conn.executemany(
            "INSERT INTO kg_edges (source, target, relation) VALUES (?, ?, ?)", KG_EDGES
        )

    eval_count = conn.execute("SELECT COUNT(*) AS c FROM eval_questions").fetchone()["c"]
    if not eval_count:
        conn.executemany(
            """
            INSERT INTO eval_questions
            (question, equipment, model, expected_source_ids, expected_fault_type,
             expected_safety_keywords)
            VALUES
            (:question, :equipment, :model, :expected_source_ids,
             :expected_fault_type, :expected_safety_keywords)
            """,
            EVAL_QUESTIONS,
        )
    conn.commit()


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _review_value(row: dict, key: str, default: str = "") -> str:
    value = row.get(key)
    return (value if value is not None else default).strip()


def apply_review_pack_if_present(
    conn: sqlite3.Connection,
    review_dir: Path | str | None = None,
) -> dict:
    target_dir = Path(review_dir) if review_dir is not None else DATA_DIR / "review"
    result = {
        "review_dir": str(target_dir),
        "cases_updated": 0,
        "eval_questions_updated": 0,
        "cases_csv": False,
        "eval_questions_csv": False,
    }

    cases_csv = target_dir / "mechanical_cases_review.csv"
    if cases_csv.exists():
        result["cases_csv"] = True
        with cases_csv.open("r", newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                row_id = _review_value(row, "id")
                if not row_id.isdigit():
                    continue
                cursor = conn.execute(
                    """
                    UPDATE maintenance_cases
                    SET review_status = ?, reviewer = ?, review_notes = ?
                    WHERE id = ?
                    """,
                    (
                        _review_value(row, "review_status", "unreviewed") or "unreviewed",
                        _review_value(row, "reviewer"),
                        _review_value(row, "review_notes"),
                        int(row_id),
                    ),
                )
                result["cases_updated"] += cursor.rowcount

    eval_csv = target_dir / "eval_questions_review.csv"
    if eval_csv.exists():
        result["eval_questions_csv"] = True
        with eval_csv.open("r", newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                row_id = _review_value(row, "id")
                if not row_id.isdigit():
                    continue
                cursor = conn.execute(
                    """
                    UPDATE eval_questions
                    SET review_status = ?, reviewer = ?, review_notes = ?
                    WHERE id = ?
                    """,
                    (
                        _review_value(row, "review_status", "unreviewed") or "unreviewed",
                        _review_value(row, "reviewer"),
                        _review_value(row, "review_notes"),
                        int(row_id),
                    ),
                )
                result["eval_questions_updated"] += cursor.rowcount

    conn.commit()
    return result


def bootstrap_demo_data(
    conn: sqlite3.Connection,
    review_dir: Path | str | None = None,
    exp_case_count: int | None = None,
    exp_eval_count: int | None = None,
    rebuild_index: bool | None = None,
) -> dict:
    from .sample_expansion import generate_sample_data

    generated = generate_sample_data(
        conn,
        case_count=exp_case_count
        if exp_case_count is not None
        else _int_env("A1_DEMO_EXP_CASE_COUNT", 121),
        eval_count=exp_eval_count
        if exp_eval_count is not None
        else _int_env("A1_DEMO_EXP_EVAL_COUNT", 100),
        rebuild_index=rebuild_index
        if rebuild_index is not None
        else _bool_env("A1_DEMO_REBUILD_INDEX_ON_STARTUP", False),
    )
    review = apply_review_pack_if_present(conn, review_dir=review_dir)
    return {"generated": generated, "review": review}


def bootstrap_demo_data_on_startup(conn: sqlite3.Connection) -> dict:
    if not _bool_env("A1_DEMO_BOOTSTRAP_ON_STARTUP", False):
        return {"enabled": False}
    result = bootstrap_demo_data(conn)
    result["enabled"] = True
    return result


def reset_demo_db(db_path: Path | str = DB_PATH) -> None:
    path = Path(db_path)
    if path.exists():
        path.unlink()
    conn = get_connection(path)
    try:
        init_db(conn)
        seed_if_empty(conn)
    finally:
        conn.close()
