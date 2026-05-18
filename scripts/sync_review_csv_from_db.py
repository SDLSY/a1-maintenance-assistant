from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_REVIEW_DIR = ROOT / "data" / "review"


def _read_existing(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    if not path.exists():
        return [], {}
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = {str(row.get("id", "")): row for row in reader if row.get("id")}
        return list(reader.fieldnames or []), rows


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _merge_review_row(existing: dict[str, str], fresh: dict[str, object], *, kind: str) -> dict[str, str]:
    row = {key: str(value if value is not None else "") for key, value in existing.items()}
    for key, value in fresh.items():
        row[key] = str(value if value is not None else "")
    status = row.get("review_status", "")
    if status == "approved" and not row.get("decision"):
        row["decision"] = "approve"
    if kind == "case":
        row.setdefault("mechanical_accuracy_score", "5" if row.get("reviewer") == "ME-R02" else "")
        row.setdefault("sop_completeness_score", "5" if row.get("reviewer") == "ME-R02" else "")
        row.setdefault("safety_score", "5" if row.get("reviewer") == "ME-R02" else "")
    else:
        if not row.get("difficulty"):
            row["difficulty"] = str(fresh.get("difficulty") or "medium")
        if status == "approved" and not row.get("expected_reference_ok"):
            row["expected_reference_ok"] = "yes"
    return row


def sync_review_csv(review_dir: Path | str = DEFAULT_REVIEW_DIR) -> dict:
    from backend.app.database import DB_PATH, get_connection, init_db, seed_if_empty

    target = Path(review_dir)
    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        seed_if_empty(conn)
        case_rows = [
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
        eval_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, question, equipment, model, expected_source_ids,
                       expected_fault_type, expected_safety_keywords, review_status,
                       reviewer, review_notes, category, difficulty
                FROM eval_questions
                ORDER BY id
                """
            ).fetchall()
        ]
    finally:
        conn.close()

    cases_path = target / "mechanical_cases_review.csv"
    eval_path = target / "eval_questions_review.csv"
    case_fields, existing_cases = _read_existing(cases_path)
    eval_fields, existing_eval = _read_existing(eval_path)

    case_core = list(case_rows[0].keys()) if case_rows else []
    eval_core = list(eval_rows[0].keys()) if eval_rows else []
    case_extra = ["decision", "mechanical_accuracy_score", "sop_completeness_score", "safety_score"]
    eval_extra = ["decision", "difficulty", "expected_reference_ok"]
    case_fields = list(dict.fromkeys([*case_fields, *case_core, *case_extra]))
    eval_fields = list(dict.fromkeys([*eval_fields, *eval_core, *eval_extra]))

    merged_cases = [
        _merge_review_row(existing_cases.get(str(row["id"]), {}), row, kind="case")
        for row in case_rows
    ]
    merged_eval = [
        _merge_review_row(existing_eval.get(str(row["id"]), {}), row, kind="eval")
        for row in eval_rows
    ]
    _write_rows(cases_path, case_fields, merged_cases)
    _write_rows(eval_path, eval_fields, merged_eval)
    return {
        "review_dir": str(target),
        "cases": len(merged_cases),
        "eval_questions": len(merged_eval),
        "cases_path": str(cases_path),
        "eval_path": str(eval_path),
    }


def main() -> int:
    print(sync_review_csv())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
