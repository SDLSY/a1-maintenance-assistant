from __future__ import annotations

import json
import os
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SupabaseConfig:
    enabled: bool
    url: str
    key_present: bool
    secret_key: str
    schema: str
    table_prefix: str

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        requested = os.getenv("SUPABASE_ENABLED", "false").strip().lower() in TRUE_VALUES
        url = (
            os.getenv("SUPABASE_URL", "").strip()
            or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").strip()
        ).rstrip("/")
        secret_key = (
            os.getenv("SUPABASE_SECRET_KEY", "").strip()
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        )
        return cls(
            enabled=requested and bool(url and secret_key),
            url=url,
            key_present=bool(secret_key),
            secret_key=secret_key,
            schema=os.getenv("SUPABASE_SCHEMA", "public").strip() or "public",
            table_prefix=os.getenv("SUPABASE_TABLE_PREFIX", "a1_").strip(),
        )

    def table(self, logical_name: str) -> str:
        return f"{self.table_prefix}{logical_name}"

    def rest_url(self, logical_name: str, query: str = "") -> str:
        target = f"{self.url}/rest/v1/{self.table(logical_name)}"
        return f"{target}?{query}" if query else target

    def headers(self, prefer: str = "") -> dict[str, str]:
        headers = {
            "apikey": self.secret_key,
            "Authorization": f"Bearer {self.secret_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.schema != "public":
            headers["Accept-Profile"] = self.schema
            headers["Content-Profile"] = self.schema
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "url": self.url,
            "schema": self.schema,
            "table_prefix": self.table_prefix,
            "key_present": self.key_present,
            "public_anon_key_present": bool(
                os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
            ),
            "tables": {
                "cases": self.table("maintenance_cases"),
                "feedback": self.table("feedback"),
            },
        }

    def sanitize(self, message: str) -> str:
        if self.secret_key:
            return message.replace(self.secret_key, "[redacted]")
        return message


def _request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict | None = None,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read().decode("utf-8")
        if not body:
            return []
        return json.loads(body)


def _disabled_result(action: str, config: SupabaseConfig) -> dict:
    return {
        "ok": False,
        "action": action,
        "enabled": False,
        "reason": "supabase disabled or credentials missing",
        "config": config.status(),
    }


def _row_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


def _case_payload(row: sqlite3.Row) -> dict:
    data = _row_dict(row)
    local_id = data.pop("id")
    data["local_id"] = local_id
    data["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    return data


def _feedback_payload(row: sqlite3.Row) -> dict:
    data = _row_dict(row)
    local_id = data.pop("id")
    data["local_id"] = local_id
    data["updated_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    return data


def _upsert(config: SupabaseConfig, logical_table: str, payload: dict) -> Any:
    return _request_json(
        "POST",
        config.rest_url(logical_table, "on_conflict=local_id"),
        config.headers("resolution=merge-duplicates,return=minimal"),
        payload,
    )


def sync_case(conn: sqlite3.Connection, case_id: int) -> dict:
    config = SupabaseConfig.from_env()
    if not config.enabled:
        return _disabled_result("sync_case", config)
    row = conn.execute("SELECT * FROM maintenance_cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        return {"ok": False, "action": "sync_case", "error": "case not found"}
    try:
        _upsert(config, "maintenance_cases", _case_payload(row))
        return {"ok": True, "action": "sync_case", "local_id": case_id, "table": config.table("maintenance_cases")}
    except Exception as exc:  # noqa: BLE001 - deployment relays vary.
        return {
            "ok": False,
            "action": "sync_case",
            "local_id": case_id,
            "table": config.table("maintenance_cases"),
            "error": config.sanitize(str(exc)),
        }


def sync_feedback(conn: sqlite3.Connection, feedback_id: int) -> dict:
    config = SupabaseConfig.from_env()
    if not config.enabled:
        return _disabled_result("sync_feedback", config)
    row = conn.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
    if row is None:
        return {"ok": False, "action": "sync_feedback", "error": "feedback not found"}
    try:
        _upsert(config, "feedback", _feedback_payload(row))
        return {"ok": True, "action": "sync_feedback", "local_id": feedback_id, "table": config.table("feedback")}
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "action": "sync_feedback",
            "local_id": feedback_id,
            "table": config.table("feedback"),
            "error": config.sanitize(str(exc)),
        }


def _select_all(config: SupabaseConfig, logical_table: str) -> list[dict]:
    query = "select=*&order=local_id.asc"
    data = _request_json("GET", config.rest_url(logical_table, query), config.headers())
    return data if isinstance(data, list) else []


def _ensure_case_graph(conn: sqlite3.Connection, case_id: int, title: str, fault_type: str) -> None:
    node_id = f"case_{case_id}"
    fault_id = f"fault_{case_id}"
    conn.execute(
        "INSERT OR IGNORE INTO kg_nodes (id, label, type) VALUES (?, ?, ?)",
        (node_id, title, "case"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO kg_nodes (id, label, type) VALUES (?, ?, ?)",
        (fault_id, fault_type, "fault"),
    )
    conn.execute(
        """
        INSERT INTO kg_edges (source, target, relation)
        SELECT ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM kg_edges WHERE source = ? AND target = ? AND relation = ?
        )
        """,
        (node_id, fault_id, "case_fault", node_id, fault_id, "case_fault"),
    )


def _upsert_local_case(conn: sqlite3.Connection, item: dict) -> bool:
    local_id = item.get("local_id")
    if not local_id:
        return False
    values = {
        "id": int(local_id),
        "title": item.get("title", ""),
        "equipment": item.get("equipment", "motor"),
        "model": item.get("model", ""),
        "symptoms": item.get("symptoms", ""),
        "fault_type": item.get("fault_type", ""),
        "cause": item.get("cause", ""),
        "actions": item.get("actions", ""),
        "parts": item.get("parts", ""),
        "risk_level": item.get("risk_level", "medium"),
        "status": item.get("status", "pending"),
        "created_at": item.get("created_at") or datetime.now(UTC).isoformat(timespec="seconds"),
        "review_status": item.get("review_status", "unreviewed"),
        "reviewer": item.get("reviewer", ""),
        "review_notes": item.get("review_notes", ""),
    }
    conn.execute(
        """
        INSERT INTO maintenance_cases
        (id, title, equipment, model, symptoms, fault_type, cause, actions, parts,
         risk_level, status, created_at, review_status, reviewer, review_notes)
        VALUES
        (:id, :title, :equipment, :model, :symptoms, :fault_type, :cause, :actions, :parts,
         :risk_level, :status, :created_at, :review_status, :reviewer, :review_notes)
        ON CONFLICT(id) DO UPDATE SET
          title=excluded.title,
          equipment=excluded.equipment,
          model=excluded.model,
          symptoms=excluded.symptoms,
          fault_type=excluded.fault_type,
          cause=excluded.cause,
          actions=excluded.actions,
          parts=excluded.parts,
          risk_level=excluded.risk_level,
          status=excluded.status,
          review_status=excluded.review_status,
          reviewer=excluded.reviewer,
          review_notes=excluded.review_notes
        """,
        values,
    )
    if values["status"] == "approved":
        _ensure_case_graph(conn, values["id"], values["title"], values["fault_type"])
    return True


def _upsert_local_feedback(conn: sqlite3.Connection, item: dict) -> bool:
    local_id = item.get("local_id")
    if not local_id:
        return False
    values = {
        "id": int(local_id),
        "question": item.get("question", ""),
        "original_answer": item.get("original_answer", ""),
        "corrected_answer": item.get("corrected_answer", ""),
        "notes": item.get("notes", ""),
        "created_at": item.get("created_at") or datetime.now(UTC).isoformat(timespec="seconds"),
    }
    conn.execute(
        """
        INSERT INTO feedback
        (id, question, original_answer, corrected_answer, notes, created_at)
        VALUES
        (:id, :question, :original_answer, :corrected_answer, :notes, :created_at)
        ON CONFLICT(id) DO UPDATE SET
          question=excluded.question,
          original_answer=excluded.original_answer,
          corrected_answer=excluded.corrected_answer,
          notes=excluded.notes
        """,
        values,
    )
    return True


def pull_mutable_data(conn: sqlite3.Connection) -> dict:
    config = SupabaseConfig.from_env()
    if not config.enabled:
        return _disabled_result("pull_mutable_data", config)
    try:
        cases = _select_all(config, "maintenance_cases")
        feedback = _select_all(config, "feedback")
        imported_cases = sum(1 for item in cases if _upsert_local_case(conn, item))
        imported_feedback = sum(1 for item in feedback if _upsert_local_feedback(conn, item))
        conn.commit()
        return {
            "ok": True,
            "action": "pull_mutable_data",
            "cases": imported_cases,
            "feedback": imported_feedback,
            "config": config.status(),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "action": "pull_mutable_data",
            "error": config.sanitize(str(exc)),
            "config": config.status(),
        }


def public_status() -> dict:
    return SupabaseConfig.from_env().status()


def sync_on_startup_enabled() -> bool:
    return os.getenv("SUPABASE_SYNC_ON_STARTUP", "true").strip().lower() in TRUE_VALUES
