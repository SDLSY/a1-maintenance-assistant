from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
from datetime import datetime

from .retrieval import tokenize

EMBEDDING_MODEL = "local-hash-embedding-v1"
DIM = 256
REMOTE_BATCH_SIZE = 64


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def local_embedding(text: str, dim: int = DIM) -> list[float]:
    vector = [0.0] * dim
    tokens = tokenize(text)
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 8) for value in vector]


def source_text(row: sqlite3.Row, source_type: str) -> str:
    if source_type == "manual":
        return " ".join(
            str(row[key] or "")
            for key in [
                "title",
                "equipment",
                "model",
                "section",
                "component",
                "fault_type",
                "content",
                "image_caption",
            ]
        )
    return " ".join(
        str(row[key] or "")
        for key in [
            "title",
            "equipment",
            "model",
            "symptoms",
            "fault_type",
            "cause",
            "actions",
            "parts",
        ]
    )


def upsert_embedding(
    conn: sqlite3.Connection,
    source_type: str,
    source_id: int,
    text: str,
    model: str = EMBEDDING_MODEL,
) -> None:
    vector = local_embedding(text)
    conn.execute(
        """
        INSERT INTO chunk_embeddings
        (source_type, source_id, model, dim, vector_json, text_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_type, source_id, model)
        DO UPDATE SET
            dim = excluded.dim,
            vector_json = excluded.vector_json,
            text_hash = excluded.text_hash,
            created_at = excluded.created_at
        """,
        (
            source_type,
            source_id,
            model,
            len(vector),
            json.dumps(vector),
            text_hash(text),
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )


def rebuild_embeddings(conn: sqlite3.Connection) -> dict:
    conn.execute("DELETE FROM chunk_embeddings")
    manual_rows = conn.execute("SELECT * FROM manual_chunks").fetchall()
    case_rows = conn.execute(
        "SELECT * FROM maintenance_cases WHERE status = 'approved'"
    ).fetchall()
    items = [("manual", row["id"], source_text(row, "manual")) for row in manual_rows]
    items += [("case", row["id"], source_text(row, "case")) for row in case_rows]
    remote_used = False
    remote_count = 0
    local_count = 0
    failed_batches: list[dict] = []
    try:
        from .model_gateway import embed_texts

        remote_model = ""
        for start in range(0, len(items), REMOTE_BATCH_SIZE):
            batch = items[start : start + REMOTE_BATCH_SIZE]
            remote = {"ok": False, "vectors": [], "error": "not attempted"}
            for attempt in range(3):
                remote = embed_texts([text for _, _, text in batch])
                if remote["ok"] and len(remote["vectors"]) == len(batch):
                    break
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
            if not remote["ok"] or len(remote["vectors"]) != len(batch):
                failed_batches.append(
                    {
                        "start": start,
                        "size": len(batch),
                        "error": str(remote.get("error") or "remote embedding batch failed")[:240],
                    }
                )
                for source_type, source_id, text in batch:
                    upsert_embedding(conn, source_type, source_id, text)
                    local_count += 1
                continue
            remote_model = remote.get("model") or remote_model
            for (source_type, source_id, text), vector in zip(batch, remote["vectors"]):
                upsert_embedding_vector(
                    conn,
                    source_type,
                    source_id,
                    text,
                    vector,
                    remote_model or "remote-embedding",
                )
                remote_count += 1
        remote_used = remote_count > 0
    except Exception:
        remote_used = False

    if remote_count == 0 and local_count == 0:
        for source_type, source_id, text in items:
            upsert_embedding(conn, source_type, source_id, text)
            local_count += 1
    conn.commit()
    return {
        "manual": len(manual_rows),
        "case": len(case_rows),
        "model": "remote" if remote_used else EMBEDDING_MODEL,
        "remote_used": remote_used,
        "remote_count": remote_count,
        "local_count": local_count,
        "failed_batches": failed_batches[:5],
    }


def upsert_embedding_vector(
    conn: sqlite3.Connection,
    source_type: str,
    source_id: int,
    text: str,
    vector: list[float],
    model: str,
) -> None:
    normalized = normalize_vector(vector)
    conn.execute(
        """
        INSERT INTO chunk_embeddings
        (source_type, source_id, model, dim, vector_json, text_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_type, source_id, model)
        DO UPDATE SET
            dim = excluded.dim,
            vector_json = excluded.vector_json,
            text_hash = excluded.text_hash,
            created_at = excluded.created_at
        """,
        (
            source_type,
            source_id,
            model,
            len(normalized),
            json.dumps(normalized),
            text_hash(text),
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )


def _load_query_embedding(conn: sqlite3.Connection, query_text: str, model: str) -> list[float] | None:
    row = conn.execute(
        "SELECT vector_json FROM query_embeddings WHERE query_hash = ? AND model = ?",
        (text_hash(query_text), model),
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["vector_json"])
    except json.JSONDecodeError:
        return None


def _save_query_embedding(
    conn: sqlite3.Connection,
    query_text: str,
    model: str,
    vector: list[float],
) -> None:
    normalized = normalize_vector(vector)
    conn.execute(
        """
        INSERT INTO query_embeddings
        (query_hash, model, dim, vector_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(query_hash, model)
        DO UPDATE SET
            dim = excluded.dim,
            vector_json = excluded.vector_json,
            created_at = excluded.created_at
        """,
        (
            text_hash(query_text),
            model,
            len(normalized),
            json.dumps(normalized),
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()


def vector_score_map(conn: sqlite3.Connection, query_text: str) -> dict[tuple[str, int], float]:
    scores: dict[tuple[str, int], float] = {}
    from .settings import settings

    model_rows = conn.execute(
        "SELECT model, COUNT(*) AS c FROM chunk_embeddings GROUP BY model ORDER BY c DESC"
    ).fetchall()
    if not model_rows:
        return scores

    query_vectors: dict[str, list[float]] = {}
    for model_row in model_rows:
        model = model_row["model"]
        if model == EMBEDDING_MODEL:
            query_vectors[model] = local_embedding(query_text)
            continue
        if not settings.remote_query_embedding_enabled:
            continue
        cached = _load_query_embedding(conn, query_text, model)
        if cached:
            query_vectors[model] = cached
            continue
        try:
            from .model_gateway import embed_texts

            remote = embed_texts([query_text])
            if remote["ok"] and remote["vectors"]:
                query_vectors[model] = normalize_vector(remote["vectors"][0])
                _save_query_embedding(conn, query_text, model, remote["vectors"][0])
        except Exception:
            continue

    rows = conn.execute(
        "SELECT source_type, source_id, model, vector_json FROM chunk_embeddings"
    ).fetchall()
    for row in rows:
        query_vector = query_vectors.get(row["model"])
        if not query_vector:
            continue
        try:
            vector = json.loads(row["vector_json"])
        except json.JSONDecodeError:
            continue
        scores[(row["source_type"], row["source_id"])] = cosine(query_vector, vector)
    return scores
