from __future__ import annotations

import csv
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_REVIEW_DIR = ROOT / "data" / "review"


def fetch_rows() -> tuple[list[dict], list[dict]]:
    from backend.app.database import DB_PATH, get_connection, init_db

    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        cases = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, title, equipment, model, symptoms, fault_type, cause, actions,
                       parts, risk_level, status, review_status, reviewer, review_notes
                FROM maintenance_cases
                ORDER BY id
                """
            ).fetchall()
        ]
        eval_questions = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, question, equipment, model, expected_source_ids,
                       expected_fault_type, expected_safety_keywords,
                       review_status, reviewer, review_notes
                FROM eval_questions
                ORDER BY id
                """
            ).fetchall()
        ]
    finally:
        conn.close()
    return cases, eval_questions


def write_csv(path: Path, rows: list[dict], extra_fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fieldnames = list(rows[0].keys()) + extra_fields
    else:
        fieldnames = extra_fields
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload = dict(row)
            for field in extra_fields:
                payload.setdefault(field, "")
            writer.writerow(payload)


def export_review_pack(review_dir: Path | str | None = None) -> dict:
    target_dir = Path(review_dir) if review_dir is not None else DEFAULT_REVIEW_DIR
    cases, eval_questions = fetch_rows()
    write_csv(
        target_dir / "mechanical_cases_review.csv",
        cases,
        ["decision", "mechanical_accuracy_score", "sop_completeness_score", "safety_score"],
    )
    write_csv(
        target_dir / "eval_questions_review.csv",
        eval_questions,
        ["decision", "difficulty", "expected_reference_ok"],
    )
    return {
        "review_dir": str(target_dir),
        "cases": len(cases),
        "eval_questions": len(eval_questions),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export mechanical review CSV files.")
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    args = parser.parse_args()

    result = export_review_pack(review_dir=args.review_dir)
    print(
        result
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
