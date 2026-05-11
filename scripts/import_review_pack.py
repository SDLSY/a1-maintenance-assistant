from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REVIEW_DIR = ROOT / "data" / "review"


def normalize_status(row: dict) -> str:
    decision = (row.get("decision") or "").strip().lower()
    status = (row.get("review_status") or "").strip().lower()
    if decision in {"approve", "approved", "通过"}:
        return "approved"
    if decision in {"reject", "rejected", "驳回"}:
        return "rejected"
    if decision in {"revise", "修改"}:
        return "needs_revision"
    return status or "unreviewed"


def import_cases(conn, path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if not row.get("id"):
                continue
            review_status = normalize_status(row)
            conn.execute(
                """
                UPDATE maintenance_cases
                SET review_status = ?, reviewer = ?, review_notes = ?
                WHERE id = ?
                """,
                (
                    review_status,
                    row.get("reviewer", ""),
                    row.get("review_notes", ""),
                    int(row["id"]),
                ),
            )
            count += 1
    return count


def import_eval_questions(conn, path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if not row.get("id"):
                continue
            review_status = normalize_status(row)
            conn.execute(
                """
                UPDATE eval_questions
                SET review_status = ?, reviewer = ?, review_notes = ?
                WHERE id = ?
                """,
                (
                    review_status,
                    row.get("reviewer", ""),
                    row.get("review_notes", ""),
                    int(row["id"]),
                ),
            )
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Import mechanical review decisions from CSV files.")
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    args = parser.parse_args()

    from backend.app.database import DB_PATH, get_connection, init_db

    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        cases = import_cases(conn, args.review_dir / "mechanical_cases_review.csv")
        eval_questions = import_eval_questions(conn, args.review_dir / "eval_questions_review.csv")
        conn.commit()
    finally:
        conn.close()
    print({"cases_updated": cases, "eval_questions_updated": eval_questions})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
