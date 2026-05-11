from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REQUIRED_EQUIPMENT = {"motor", "pump", "bearing"}
REQUIRED_APPROVED_CASES = 100
REQUIRED_APPROVED_EVAL = 100
FORBIDDEN_ARCHIVE_NAMES = {".env", ".env.local", "data/maintenance.db", "data/test-maintenance.db"}
FORBIDDEN_ARCHIVE_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".pdf", ".zip")
FORBIDDEN_ARCHIVE_PARTS = ("__pycache__/", ".venv/", ".pytest_cache/", "node_modules/", "dist/")


def _count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _check(status: str, evidence: str, *, required: bool = True) -> dict:
    return {"status": status, "evidence": evidence, "required": required}


def _manifest_summary() -> dict:
    manifest_path = ROOT / "data" / "sources" / "public_manual_sources.json"
    if not manifest_path.exists():
        return {"active_sources": 0, "equipment": [], "exists": False}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = [source for source in payload.get("sources", []) if source.get("active", True)]
    return {
        "active_sources": len(sources),
        "equipment": sorted({source.get("equipment", "") for source in sources}),
        "exists": True,
    }


def _db_summary(db_path: Path | None = None) -> dict:
    from backend.app.database import DB_PATH, get_connection, init_db
    from backend.app.evaluation import review_summary

    target = Path(db_path) if db_path is not None else DB_PATH
    conn = get_connection(target)
    try:
        init_db(conn)
        review = review_summary(conn)
        embedding_models = {
            row["model"]: row["c"]
            for row in conn.execute(
                "SELECT model, COUNT(*) AS c FROM chunk_embeddings GROUP BY model"
            ).fetchall()
        }
        return {
            "db_path": str(target),
            "documents": conn.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"],
            "manual_chunks": conn.execute("SELECT COUNT(*) AS c FROM manual_chunks").fetchone()["c"],
            "chunks_with_source_url": conn.execute(
                "SELECT COUNT(*) AS c FROM manual_chunks WHERE source_url <> ''"
            ).fetchone()["c"],
            "cases_total": review["cases"]["total"],
            "cases_approved": review["cases"]["approved"],
            "cases_unreviewed": review["cases"]["unreviewed"],
            "eval_total": review["eval_questions"]["total"],
            "eval_approved": review["eval_questions"]["approved"],
            "eval_unreviewed": review["eval_questions"]["unreviewed"],
            "embedding_models": embedding_models,
        }
    finally:
        conn.close()


def _provider_summary() -> dict:
    from backend.app.model_gateway import agent_route_report, safe_provider_report

    routes = agent_route_report()
    providers = safe_provider_report()
    active_remote_routes = [
        route
        for route in routes
        if route["provider"] != "local" and route["supported"] and route["key_present"]
    ]
    return {
        "routes": routes,
        "providers": providers,
        "active_remote_role_count": len(active_remote_routes),
        "embedding_route": next((route for route in routes if route["role"] == "embedding"), {}),
    }


def _submission_summary(submission_archive: Path | str | None) -> dict:
    if submission_archive is None:
        return {"exists": False, "entries": 0, "forbidden_entries": [], "has_manifest": False}
    archive = Path(submission_archive)
    if not archive.exists():
        return {"exists": False, "entries": 0, "forbidden_entries": [], "has_manifest": False}
    with ZipFile(archive) as package:
        names = [entry.filename for entry in package.infolist()]
    forbidden = [
        name
        for name in names
        if name in FORBIDDEN_ARCHIVE_NAMES
        or name.endswith(FORBIDDEN_ARCHIVE_SUFFIXES)
        or any(part in name for part in FORBIDDEN_ARCHIVE_PARTS)
    ]
    return {
        "exists": True,
        "path": str(archive),
        "entries": len(names),
        "forbidden_entries": forbidden,
        "has_manifest": "SUBMISSION_MANIFEST.md" in names,
        "has_env_example": ".env.example" in names,
        "has_source_manifest": "data/sources/public_manual_sources.json" in names,
        "has_case_review_csv": "data/review/mechanical_cases_review.csv" in names,
        "has_eval_review_csv": "data/review/eval_questions_review.csv" in names,
        "has_image_eval_manifest": "data/image_eval/fault_image_eval_manifest.csv" in names,
        "has_image_eval_readme": "data/image_eval/README.md" in names,
        "has_image_eval_report": "docs/IMAGE_EVAL_STATUS.md" in names,
        "has_public_deploy_doc": "docs/DEPLOYMENT_PUBLIC.md" in names,
        "has_supabase_schema": "docs/SUPABASE_SCHEMA.sql" in names,
        "has_render_yaml": "render.yaml" in names,
        "has_cloudflare_prepare_script": "scripts/prepare_cloudflare_site.py" in names,
    }


def _image_eval_summary() -> dict:
    from scripts.image_eval_status import summarize_manifest

    return summarize_manifest()


def run_audit(
    *,
    submission_archive: Path | str | None = None,
    db_path: Path | str | None = None,
    deployment_mode: str = "full",
) -> dict:
    if deployment_mode not in {"full", "public"}:
        raise ValueError("deployment_mode must be 'full' or 'public'")
    db = _db_summary(Path(db_path) if db_path is not None else None)
    manifest = _manifest_summary()
    providers = _provider_summary()
    submission = _submission_summary(submission_archive)
    image_eval = _image_eval_summary()

    review_case_rows = _count_csv_rows(ROOT / "data" / "review" / "mechanical_cases_review.csv")
    review_eval_rows = _count_csv_rows(ROOT / "data" / "review" / "eval_questions_review.csv")
    machine = platform.machine()
    loongarch_validated = "loong" in machine.lower() or bool(
        str(platform.platform()).lower().find("loongarch") >= 0
    )
    loongarch_required = deployment_mode != "public"

    checks = {
        "web_system": _check(
            "pass"
            if (ROOT / "backend" / "app" / "main.py").exists()
            and (ROOT / "frontend" / "index.html").exists()
            else "fail",
            "FastAPI backend and Vue static frontend files are present.",
        ),
        "public_sources": _check(
            "pass"
            if manifest["active_sources"] >= 8 and REQUIRED_EQUIPMENT <= set(manifest["equipment"])
            else "fail",
            f"{manifest['active_sources']} active public sources; equipment={manifest['equipment']}.",
        ),
        "document_index": _check(
            "pass" if db["manual_chunks"] >= 8 else "fail",
            f"{db['manual_chunks']} manual chunks; {db['chunks_with_source_url']} have source URLs.",
        ),
        "cloud_model_routes": _check(
            "pass" if providers["active_remote_role_count"] >= 5 else "warn",
            f"{providers['active_remote_role_count']} remote role routes are supported with keys.",
        ),
        "openrouter_embedding": _check(
            "pass"
            if providers["embedding_route"].get("provider") == "openrouter"
            and providers["embedding_route"].get("key_present")
            else "warn",
            str(providers["embedding_route"]),
        ),
        "case_and_eval_assets": _check(
            "pass" if review_case_rows >= 100 and review_eval_rows >= 100 else "fail",
            f"review CSV rows: cases={review_case_rows}, eval_questions={review_eval_rows}.",
        ),
        "mechanical_review": _check(
            "pass"
            if db["cases_approved"] >= REQUIRED_APPROVED_CASES
            and db["eval_approved"] >= REQUIRED_APPROVED_EVAL
            else "blocked",
            (
                f"approved cases={db['cases_approved']}/{REQUIRED_APPROVED_CASES}; "
                f"approved eval={db['eval_approved']}/{REQUIRED_APPROVED_EVAL}; "
                f"unreviewed cases={db['cases_unreviewed']}, eval={db['eval_unreviewed']}."
            ),
        ),
        "submission_package": _check(
            "pass"
            if submission["exists"]
            and not submission["forbidden_entries"]
            and submission["has_manifest"]
            and submission["has_env_example"]
            and submission["has_source_manifest"]
            and submission["has_case_review_csv"]
            and submission["has_eval_review_csv"]
            and submission["has_image_eval_manifest"]
            and submission["has_image_eval_readme"]
            and submission["has_image_eval_report"]
            else "fail",
            (
                f"exists={submission['exists']}; entries={submission['entries']}; "
                f"forbidden={len(submission['forbidden_entries'])}."
            ),
        ),
        "image_eval_assets": _check(
            "pass" if image_eval["ready"] else "blocked",
            (
                f"rows={image_eval['total']}; available={image_eval['available_images']}/"
                f"{image_eval['required_images']}; approved={image_eval['approved_images']}/"
                f"{image_eval['required_images']}; missing={image_eval['missing_images']}."
            ),
        ),
        "public_demo_deployment": _check(
            "pass"
            if submission["exists"]
            and submission.get("has_public_deploy_doc")
            and submission.get("has_supabase_schema")
            and submission.get("has_render_yaml")
            and submission.get("has_cloudflare_prepare_script")
            else "fail",
            (
                f"public_doc={submission.get('has_public_deploy_doc', False)}; "
                f"supabase_schema={submission.get('has_supabase_schema', False)}; "
                f"render_yaml={submission.get('has_render_yaml', False)}; "
                f"cloudflare_script={submission.get('has_cloudflare_prepare_script', False)}."
            ),
            required=deployment_mode == "public",
        ),
        "loongarch_runtime": _check(
            "pass" if loongarch_validated else "blocked",
            f"current platform={platform.platform()}, machine={machine}.",
            required=loongarch_required,
        ),
    }

    missing_resources: list[str] = []
    if checks["mechanical_review"]["status"] != "pass":
        missing_resources.append("机械专业队友需审核并回写至少 100 条案例和 100 条评测题。")
    if checks["loongarch_runtime"]["required"] and checks["loongarch_runtime"]["status"] != "pass":
        missing_resources.append("需要 LoongArch + 银河麒麟实机运行 check_deploy.py 与完整演示链路。")
    if checks["cloud_model_routes"]["status"] != "pass":
        missing_resources.append("需要确认云端文本/视觉/embedding 模型 key 与路由在目标环境可用。")

    if checks["image_eval_assets"]["status"] != "pass":
        missing_resources.append(
            "Need 30 authorized and mechanically approved fault images under data/image_eval/images/ "
            "for the multimodal image evaluation gate."
        )

    required_statuses = [check["status"] for check in checks.values() if check["required"]]
    ready = all(status == "pass" for status in required_statuses)

    return {
        "ready": ready,
        "deployment_mode": deployment_mode,
        "summary": {
            **db,
            "active_public_sources": manifest["active_sources"],
            "public_source_equipment": manifest["equipment"],
            "review_case_rows": review_case_rows,
            "review_eval_rows": review_eval_rows,
            "image_eval_rows": image_eval["total"],
            "image_eval_available": image_eval["available_images"],
            "image_eval_approved": image_eval["approved_images"],
            "image_eval_missing": image_eval["missing_images"],
            "submission_entries": submission["entries"],
            "submission_forbidden_entries": len(submission["forbidden_entries"]),
        },
        "checks": checks,
        "missing_resources": missing_resources,
        "providers": providers,
        "submission": submission,
    }


def write_markdown_report(result: dict, output_path: Path | str) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# A1 Readiness Audit",
        "",
        f"Ready: `{result['ready']}`",
        f"Deployment mode: `{result.get('deployment_mode', 'full')}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "|---|---|---|",
    ]
    for name, check in result["checks"].items():
        evidence = str(check["evidence"]).replace("\n", " ")
        lines.append(f"| `{name}` | `{check['status']}` | {evidence} |")

    lines.extend(["", "## Missing Resources", ""])
    if result["missing_resources"]:
        lines.extend(f"- {item}" for item in result["missing_resources"])
    else:
        lines.append("- None")

    lines.extend(["", "## Summary", "", "```json"])
    lines.append(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    lines.append("```")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit A1 project readiness against deliverables.")
    parser.add_argument("--submission-archive", type=Path, default=None)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--deployment-mode", choices=("full", "public"), default="full")
    parser.add_argument("--report", type=Path, default=ROOT / "docs" / "READINESS_AUDIT.md")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a short summary.")
    args = parser.parse_args()

    result = run_audit(
        submission_archive=args.submission_archive,
        db_path=args.db_path,
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
                    "missing_resources": result["missing_resources"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
