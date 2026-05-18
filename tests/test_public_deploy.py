from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from backend.app.database import init_db


def test_supabase_config_is_disabled_without_url_or_key(monkeypatch) -> None:
    from backend.app.supabase_sync import SupabaseConfig

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_ENABLED", "true")

    config = SupabaseConfig.from_env()

    assert config.enabled is False
    assert config.status()["enabled"] is False
    assert config.status()["key_present"] is False
    assert "sk-" not in json.dumps(config.status()).lower()


def test_supabase_config_builds_prefixed_rest_url(monkeypatch) -> None:
    from backend.app.supabase_sync import SupabaseConfig

    monkeypatch.setenv("SUPABASE_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co/")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-secret-token")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "legacy-service-role-key")
    monkeypatch.setenv("SUPABASE_TABLE_PREFIX", "a1_")

    config = SupabaseConfig.from_env()

    assert config.enabled is True
    assert config.table("maintenance_cases") == "a1_maintenance_cases"
    assert config.rest_url("maintenance_cases") == "https://demo.supabase.co/rest/v1/a1_maintenance_cases"
    assert config.status()["key_present"] is True
    assert "test-secret-token" not in json.dumps(config.status())


def test_supabase_config_accepts_previous_project_env_names(monkeypatch) -> None:
    from backend.app.supabase_sync import SupabaseConfig

    monkeypatch.setenv("SUPABASE_ENABLED", "true")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_URL", "https://legacy.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "legacy-service-token")

    config = SupabaseConfig.from_env()

    assert config.enabled is True
    assert config.url == "https://legacy.supabase.co"
    assert config.status()["key_present"] is True
    assert "legacy-service-token" not in json.dumps(config.status())


def test_supabase_config_does_not_enable_server_sync_with_anon_key_only(monkeypatch) -> None:
    from backend.app.supabase_sync import SupabaseConfig

    monkeypatch.setenv("SUPABASE_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-only-token")
    monkeypatch.setenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "legacy-anon-only-token")

    config = SupabaseConfig.from_env()

    assert config.enabled is False
    assert config.status()["key_present"] is False


def test_sync_case_upserts_local_case_to_supabase(monkeypatch, tmp_path) -> None:
    from backend.app import supabase_sync

    db_path = tmp_path / "cases.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    cursor = conn.execute(
        """
        INSERT INTO maintenance_cases
        (title, equipment, model, symptoms, fault_type, cause, actions, parts,
         risk_level, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "现场新增：泵密封泄漏",
            "pump",
            "ISG80-160",
            "密封处连续滴漏",
            "泄漏",
            "密封圈老化",
            "停机泄压后更换密封组件",
            "机械密封组件",
            "high",
            "pending",
            "2026-05-11T17:12:00",
        ),
    )
    case_id = cursor.lastrowid
    conn.commit()

    calls: list[dict] = []

    monkeypatch.setenv("SUPABASE_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-secret-token")
    monkeypatch.setenv("SUPABASE_TABLE_PREFIX", "a1_")
    monkeypatch.setattr(
        supabase_sync,
        "_request_json",
        lambda method, url, headers, payload=None: calls.append(
            {"method": method, "url": url, "headers": headers, "payload": payload}
        )
        or [],
    )

    result = supabase_sync.sync_case(conn, case_id)

    assert result["ok"] is True
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/rest/v1/a1_maintenance_cases?on_conflict=local_id")
    assert calls[0]["payload"]["local_id"] == case_id
    assert calls[0]["payload"]["title"] == "现场新增：泵密封泄漏"
    assert calls[0]["payload"]["status"] == "pending"
    assert "test-secret-token" not in json.dumps(result)
    conn.close()


def test_sync_case_retries_legacy_supabase_schema_without_work_order_columns(monkeypatch, tmp_path) -> None:
    from backend.app import supabase_sync

    db_path = tmp_path / "cases.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    cursor = conn.execute(
        """
        INSERT INTO maintenance_cases
        (title, equipment, model, symptoms, fault_type, cause, actions, parts,
         risk_level, status, work_order_status, approved_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "演示验收：电机端盖油污",
            "motor",
            "Y2-160M",
            "端盖油污和温升",
            "过热/油污",
            "密封老化",
            "停机断电挂牌后拆检端盖",
            "密封圈",
            "medium",
            "approved",
            "archived",
            "2026-05-12T09:00:00",
            "2026-05-12T08:00:00",
        ),
    )
    case_id = cursor.lastrowid
    conn.commit()

    calls: list[dict] = []

    monkeypatch.setenv("SUPABASE_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-secret-token")
    monkeypatch.setenv("SUPABASE_TABLE_PREFIX", "a1_")

    def fake_request(method, url, headers, payload=None):
        calls.append({"method": method, "url": url, "headers": headers, "payload": payload})
        if len(calls) == 1:
            raise RuntimeError("HTTP 400: Could not find the 'approved_at' column")
        return []

    monkeypatch.setattr(supabase_sync, "_request_json", fake_request)

    result = supabase_sync.sync_case(conn, case_id)

    assert result["ok"] is True
    assert result["fallback"] == "legacy_case_columns"
    assert len(calls) == 2
    assert "approved_at" in calls[0]["payload"]
    assert "work_order_status" in calls[0]["payload"]
    assert "approved_at" not in calls[1]["payload"]
    assert "work_order_status" not in calls[1]["payload"]
    conn.close()


def test_supabase_pull_preserves_local_approval_when_remote_is_unreviewed(monkeypatch, tmp_path) -> None:
    from backend.app import supabase_sync

    db_path = tmp_path / "pull-preserve.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.execute(
        """
        INSERT INTO maintenance_cases
        (id, title, equipment, model, symptoms, fault_type, cause, actions, parts,
         risk_level, status, created_at, review_status, reviewer, review_notes,
         work_order_status, approved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            7,
            "local approved case",
            "pump",
            "ISG80-160",
            "seal leak",
            "leakage",
            "seal wear",
            "replace seal",
            "mechanical seal",
            "high",
            "approved",
            "2026-05-12T08:00:00",
            "approved",
            "ME-R02",
            "checked locally",
            "archived",
            "2026-05-12T09:00:00",
        ),
    )
    conn.commit()

    monkeypatch.setenv("SUPABASE_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://demo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-secret-token")

    def fake_request(method, url, headers, payload=None):
        if "maintenance_cases" in url:
            return [
                {
                    "local_id": 7,
                    "title": "remote older case",
                    "equipment": "pump",
                    "model": "ISG80-160",
                    "symptoms": "seal leak",
                    "fault_type": "leakage",
                    "cause": "seal wear",
                    "actions": "replace seal",
                    "parts": "mechanical seal",
                    "risk_level": "high",
                    "status": "pending",
                    "review_status": "unreviewed",
                    "reviewer": "",
                    "review_notes": "",
                }
            ]
        if "feedback" in url:
            return []
        return []

    monkeypatch.setattr(supabase_sync, "_request_json", fake_request)

    result = supabase_sync.pull_mutable_data(conn)
    row = conn.execute("SELECT * FROM maintenance_cases WHERE id = 7").fetchone()

    assert result["ok"] is True
    assert row["title"] == "remote older case"
    assert row["review_status"] == "approved"
    assert row["reviewer"] == "ME-R02"
    assert row["review_notes"] == "checked locally"
    assert row["work_order_status"] == "archived"
    conn.close()


def test_prepare_cloudflare_site_generates_static_config(tmp_path) -> None:
    from scripts.prepare_cloudflare_site import prepare_cloudflare_site

    output = prepare_cloudflare_site(
        output_dir=tmp_path / "site",
        api_base_url="https://a1-api.example.com/",
    )

    assert (output / "index.html").exists()
    assert (output / "static" / "app.js").exists()
    assert (output / "static" / "styles.css").exists()
    assert (output / "static" / "vendor" / "vue.global.prod.js").exists()
    config_text = (output / "static" / "config.js").read_text(encoding="utf-8")
    assert 'window.A1_API_BASE_URL = "https://a1-api.example.com";' in config_text
    assert "sk-" not in config_text.lower()


def test_submission_package_includes_supabase_migration(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package

    archive = build_submission_package(output_dir=tmp_path, timestamp="public-deploy")

    import zipfile

    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())

    assert "supabase/migrations/0001_a1_public_demo.sql" in names


def test_cloud_bootstrap_generates_reviewed_demo_data(tmp_path) -> None:
    from backend.app.database import bootstrap_demo_data, seed_if_empty
    from backend.app.evaluation import review_summary

    db_path = tmp_path / "cloud-bootstrap.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        seed_if_empty(conn)

        result = bootstrap_demo_data(
            conn,
            review_dir=Path(__file__).resolve().parents[1] / "data" / "review",
            exp_case_count=121,
            exp_eval_count=100,
            rebuild_index=False,
        )
        review = review_summary(conn)
        case_total = conn.execute("SELECT COUNT(*) AS c FROM maintenance_cases").fetchone()["c"]
        eval_total = conn.execute("SELECT COUNT(*) AS c FROM eval_questions").fetchone()["c"]

        assert result["generated"]["target_cases"] == 121
        assert result["review"]["cases_updated"] >= 100
        assert result["review"]["eval_questions_updated"] >= 100
        assert case_total >= 125
        assert eval_total >= 104
        assert review["cases"]["approved"] >= 100
        assert review["eval_questions"]["approved"] >= 100
    finally:
        conn.close()
