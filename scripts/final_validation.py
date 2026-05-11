from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs" / "FINAL_VALIDATION_REPORT.md"
sys.path.insert(0, str(ROOT))


def collect_final_validation(
    *,
    submission_archive: Path | str | None = None,
    api_base_url: str = "http://127.0.0.1:8051",
    deployment_mode: str = "full",
) -> dict:
    from scripts.audit_readiness import run_audit
    from scripts.loongarch_acceptance import collect_acceptance
    from scripts.review_progress import summarize_review_dir

    if deployment_mode not in {"full", "public"}:
        raise ValueError("deployment_mode must be 'full' or 'public'")

    readiness = run_audit(submission_archive=submission_archive, deployment_mode=deployment_mode)
    review = summarize_review_dir()
    loongarch = collect_acceptance(api_base_url=api_base_url)

    blockers: list[str] = []
    for name, check in readiness["checks"].items():
        if check["required"] and check["status"] != "pass":
            blockers.append(name)
    if readiness["checks"]["mechanical_review"]["status"] != "pass":
        blockers.append("mechanical_review")
    if deployment_mode != "public" and readiness["checks"]["loongarch_runtime"]["status"] != "pass":
        blockers.append("loongarch_runtime")
    if not review["ready_for_goal"]:
        blockers.append("review_csv_goal")
    if deployment_mode != "public" and not loongarch["loongarch_validated"]:
        blockers.append("loongarch_acceptance")

    blockers = sorted(set(blockers))
    ready = readiness["ready"] and review["ready_for_goal"] and (
        loongarch["loongarch_validated"] if deployment_mode != "public" else True
    )
    return {
        "ready": ready,
        "deployment_mode": deployment_mode,
        "blockers": blockers,
        "readiness": {
            "ready": readiness["ready"],
            "checks": {name: check["status"] for name, check in readiness["checks"].items()},
            "missing_resources": readiness["missing_resources"],
        },
        "review": {
            "ready_for_goal": review["ready_for_goal"],
            "cases_approved": review["cases"]["approved"],
            "eval_approved": review["eval_questions"]["approved"],
            "missing": review["missing"],
        },
        "loongarch": {
            "loongarch_validated": loongarch["loongarch_validated"],
            "checks": {name: check["status"] for name, check in loongarch["checks"].items()},
        },
        "submission": {
            "submission_entries": readiness["summary"]["submission_entries"],
            "submission_forbidden_entries": readiness["summary"]["submission_forbidden_entries"],
        },
    }


def write_markdown_report(result: dict, output_path: Path | str = DEFAULT_REPORT) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Final Validation Report",
        "",
        f"ready: `{result['ready']}`",
        f"deployment_mode: `{result.get('deployment_mode', 'full')}`",
        "",
        "## Blockers",
        "",
    ]
    if result["blockers"]:
        lines.extend(f"- `{item}`" for item in result["blockers"])
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Area | Status |",
            "|---|---|",
            f"| readiness | `{result['readiness']['ready']}` |",
            f"| review_csv_goal | `{result['review']['ready_for_goal']}` |",
            f"| loongarch_acceptance | `{result['loongarch']['loongarch_validated']}` |",
            f"| submission_forbidden_entries | `{result['submission']['submission_forbidden_entries']}` |",
            "",
            "## Raw Result",
            "",
            "```json",
            json.dumps(result, ensure_ascii=False, indent=2),
            "```",
        ]
    )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Run final project validation summary.")
    parser.add_argument("--submission-archive", type=Path, default=None)
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8051")
    parser.add_argument("--deployment-mode", choices=("full", "public"), default="full")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = collect_final_validation(
        submission_archive=args.submission_archive,
        api_base_url=args.api_base_url,
        deployment_mode=args.deployment_mode,
    )
    write_markdown_report(result, args.report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "ready": result["ready"],
                    "report": str(args.report),
                    "blockers": result["blockers"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
