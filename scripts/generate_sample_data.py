from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import DB_PATH, get_connection, init_db, seed_if_empty  # noqa: E402
from app.sample_expansion import generate_sample_data  # noqa: E402


def main() -> None:
    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        seed_if_empty(conn)
        result = generate_sample_data(conn)
    finally:
        conn.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

