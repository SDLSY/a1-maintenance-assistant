from __future__ import annotations

import json
import sqlite3
import urllib.request


def test_vector_query_skips_remote_embedding_by_default(monkeypatch) -> None:
    from backend.app import vector_index
    from backend.app.settings import settings

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE chunk_embeddings (
            source_type TEXT,
            source_id INTEGER,
            model TEXT,
            vector_json TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO chunk_embeddings VALUES (?, ?, ?, ?)",
        ("manual", 1, "qwen/qwen3-embedding-8b", json.dumps([1.0, 0.0])),
    )
    calls = {"count": 0}

    def fake_embed_texts(texts: list[str]) -> dict:
        calls["count"] += 1
        return {"ok": True, "vectors": [[1.0, 0.0]], "model": "qwen/qwen3-embedding-8b"}

    monkeypatch.setattr("backend.app.model_gateway.embed_texts", fake_embed_texts)
    monkeypatch.setattr(settings, "remote_query_embedding_enabled", False)

    assert vector_index.vector_score_map(conn, "轴承剥落") == {}
    assert calls["count"] == 0


def test_request_json_accepts_short_timeout(monkeypatch) -> None:
    from backend.app import model_gateway

    calls: dict[str, float] = {}

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"ok": true}'

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        calls["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = model_gateway._request_json(
        "https://example.invalid/test",
        {"Accept": "application/json"},
        {"hello": "world"},
        timeout_seconds=3.5,
    )

    assert result == {"ok": True}
    assert calls["timeout"] == 3.5


def test_frontend_exposes_query_error_state() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app_js = (root / "frontend" / "app.js").read_text(encoding="utf-8")
    index = (root / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "queryError" in app_js
    assert "catch (error)" in app_js
    assert "queryError" in index
