from __future__ import annotations

import importlib.util
import json
import platform
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import DB_PATH, get_connection, init_db, seed_if_empty  # noqa: E402
from app.model_gateway import safe_provider_report  # noqa: E402
from app.supabase_sync import public_status as supabase_public_status  # noqa: E402


def module_status(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> None:
    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        seed_if_empty(conn)
        sqlite_version = sqlite3.sqlite_version
    finally:
        conn.close()

    report = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "loongarch_like": "loong" in platform.machine().lower(),
        "sqlite": sqlite_version,
        "modules": {
            "fastapi": module_status("fastapi"),
            "uvicorn": module_status("uvicorn"),
            "pypdf": module_status("pypdf"),
            "neo4j": module_status("neo4j"),
        },
        "providers": safe_provider_report(),
        "supabase": supabase_public_status(),
        "db_path": str(DB_PATH),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
