from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.database import DB_PATH, get_connection, init_db, seed_if_empty  # noqa: E402
from backend.app.graph_store import get_graph_store  # noqa: E402
from backend.app.image_eval_assets import ensure_image_eval_visual_assets  # noqa: E402


def import_image_eval_assets(*, rebuild_graph: bool = True) -> dict:
    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        seed_if_empty(conn)
        result = ensure_image_eval_visual_assets(conn)
        if rebuild_graph:
            result["graph_rebuild"] = get_graph_store(conn).rebuild()
        return result
    finally:
        conn.close()


def main() -> int:
    result = import_image_eval_assets()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
