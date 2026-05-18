from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.a1_makg_samples import ensure_a1_makg_samples
from backend.app.database import DB_PATH, get_connection, init_db, seed_if_empty
from backend.app.ingestion import ingest_directory


def apply_upgrade() -> dict:
    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        seed_if_empty(conn)
        samples = ensure_a1_makg_samples(conn)
        ingestion = ingest_directory(conn, rebuild=False)
        return {
            "db": str(DB_PATH),
            "samples": samples,
            "ingestion": ingestion,
        }
    finally:
        conn.close()


def main() -> int:
    result = apply_upgrade()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
