from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_DIR = ROOT / "data" / "review"
DEFAULT_REPORT = ROOT / "docs" / "MECHANICAL_REVIEW_STATUS.md"

STATUS_ORDER = ("approved", "needs_revision", "rejected", "unreviewed", "invalid")


def normalize_status(row: dict) -> str:
    decision = (row.get("decision") or "").strip().lower()
    status = (row.get("review_status") or "").strip().lower()
    if decision in {"approve", "approved"}:
        return "approved"
    if decision in {"revise", "revision", "needs_revision"}:
        return "needs_revision"
    if decision in {"reject", "rejected"}:
        return "rejected"
    if status in {"approved", "needs_revision", "rejected", "unreviewed"}:
        return status
    if not decision and not status:
        return "unreviewed"
    return "invalid"


def summarize_csv(path: Path) -> dict:
    counts = {status: 0 for status in STATUS_ORDER}
    rows = 0
    reviewers: set[str] = set()
    missing_notes = 0
    if not path.exists():
        return {
            "exists": False,
            "total": 0,
            **counts,
            "reviewed": 0,
            "reviewers": [],
            "missing_notes": 0,
        }

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            rows += 1
            status = normalize_status(row)
            counts[status] += 1
            reviewer = (row.get("reviewer") or "").strip()
            if reviewer:
                reviewers.add(reviewer)
            if status in {"needs_revision", "rejected"} and not (row.get("review_notes") or "").strip():
                missing_notes += 1

    reviewed = counts["approved"] + counts["needs_revision"] + counts["rejected"]
    return {
        "exists": True,
        "total": rows,
        **counts,
        "reviewed": reviewed,
        "reviewers": sorted(reviewers),
        "missing_notes": missing_notes,
    }


def summarize_review_dir(
    review_dir: Path | str = DEFAULT_REVIEW_DIR,
    *,
    required_cases: int = 150,
    required_eval_questions: int = 130,
) -> dict:
    target = Path(review_dir)
    cases = summarize_csv(target / "mechanical_cases_review.csv")
    eval_questions = summarize_csv(target / "eval_questions_review.csv")
    ready_for_import = (
        cases["exists"]
        and eval_questions["exists"]
        and cases["reviewed"] > 0
        and eval_questions["reviewed"] > 0
        and cases["invalid"] == 0
        and eval_questions["invalid"] == 0
    )
    ready_for_goal = (
        cases["approved"] >= required_cases and eval_questions["approved"] >= required_eval_questions
    )
    missing: list[str] = []
    if cases["approved"] < required_cases:
        missing.append(f"案例 approved 还差 {required_cases - cases['approved']} 条。")
    if eval_questions["approved"] < required_eval_questions:
        missing.append(f"评测题 approved 还差 {required_eval_questions - eval_questions['approved']} 条。")
    if cases["invalid"] or eval_questions["invalid"]:
        missing.append("存在无法识别的 review_status/decision，请修正为 approved/needs_revision/rejected/unreviewed。")
    if cases["missing_notes"] or eval_questions["missing_notes"]:
        missing.append("needs_revision/rejected 行建议填写 review_notes，便于回改。")

    return {
        "review_dir": str(target),
        "ready_for_import": ready_for_import,
        "ready_for_goal": ready_for_goal,
        "required_cases": required_cases,
        "required_eval_questions": required_eval_questions,
        "cases": cases,
        "eval_questions": eval_questions,
        "missing": missing,
    }


def write_markdown_report(result: dict, output_path: Path | str = DEFAULT_REPORT) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Mechanical Review Progress",
        "",
        f"ready_for_import: `{result['ready_for_import']}`",
        f"ready_for_goal: `{result['ready_for_goal']}`",
        "",
        "| Dataset | Total | Reviewed | Approved | Needs revision | Rejected | Unreviewed | Invalid |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, key in (("Cases", "cases"), ("Eval questions", "eval_questions")):
        item = result[key]
        lines.append(
            "| {label} | {total} | {reviewed} | {approved} | {needs_revision} | "
            "{rejected} | {unreviewed} | {invalid} |".format(label=label, **item)
        )
    lines.extend(["", "## Missing", ""])
    if result["missing"]:
        lines.extend(f"- {item}" for item in result["missing"])
    else:
        lines.append("- None")
    lines.extend(["", "## Raw Summary", "", "```json"])
    lines.append(json.dumps(result, ensure_ascii=False, indent=2))
    lines.append("```")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize mechanical review CSV progress.")
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = summarize_review_dir(args.review_dir)
    write_markdown_report(result, args.report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "ready_for_import": result["ready_for_import"],
                    "ready_for_goal": result["ready_for_goal"],
                    "report": str(args.report),
                    "missing": result["missing"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0 if result["ready_for_goal"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
