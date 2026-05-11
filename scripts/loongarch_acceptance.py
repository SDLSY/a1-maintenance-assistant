from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs" / "LOONGARCH_ACCEPTANCE_REPORT.md"
sys.path.insert(0, str(ROOT))


def _module_status(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _api_get(base_url: str, path: str) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _check(status: str, evidence: str) -> dict:
    return {"status": status, "evidence": evidence}


def _db_counts() -> dict:
    from backend.app.database import DB_PATH, get_connection, init_db

    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        return {
            "db_path": str(DB_PATH),
            "documents": conn.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"],
            "manual_chunks": conn.execute("SELECT COUNT(*) AS c FROM manual_chunks").fetchone()["c"],
            "cases": conn.execute("SELECT COUNT(*) AS c FROM maintenance_cases").fetchone()["c"],
            "eval_questions": conn.execute("SELECT COUNT(*) AS c FROM eval_questions").fetchone()["c"],
            "embedding_rows": conn.execute("SELECT COUNT(*) AS c FROM chunk_embeddings").fetchone()["c"],
        }
    finally:
        conn.close()


def collect_acceptance(api_base_url: str = "http://127.0.0.1:8051") -> dict:
    from backend.app.model_gateway import agent_route_report, safe_provider_report

    machine = platform.machine()
    platform_text = platform.platform()
    loongarch_like = "loong" in machine.lower() or "loongarch" in platform_text.lower()
    modules = {
        "fastapi": _module_status("fastapi"),
        "uvicorn": _module_status("uvicorn"),
        "pypdf": _module_status("pypdf"),
        "sqlite3": True,
    }
    db = _db_counts()
    routes = agent_route_report()
    providers = safe_provider_report()

    api: dict = {"enabled": bool(api_base_url), "base_url": api_base_url, "ok": False}
    if api_base_url:
        try:
            api["health"] = _api_get(api_base_url, "/api/health")
            api["routing"] = _api_get(api_base_url, "/api/agent-routing")
            api["review_status"] = _api_get(api_base_url, "/api/review-status")
            api["ok"] = True
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            api["error"] = str(exc)

    checks = {
        "platform": _check(
            "pass" if loongarch_like else "blocked",
            f"platform={platform_text}; machine={machine}",
        ),
        "python_modules": _check(
            "pass" if all(modules.values()) else "fail",
            json.dumps(modules, ensure_ascii=False),
        ),
        "database": _check(
            "pass" if db["manual_chunks"] > 0 and db["cases"] > 0 else "fail",
            json.dumps(db, ensure_ascii=False),
        ),
        "model_routes": _check(
            "pass"
            if all(route["supported"] and route["key_present"] for route in routes if route["provider"] != "local")
            else "warn",
            json.dumps(routes, ensure_ascii=False),
        ),
        "api": _check(
            "pass" if api["ok"] else ("skipped" if not api_base_url else "blocked"),
            api.get("error") or f"base_url={api_base_url}; ok={api['ok']}",
        ),
    }
    loongarch_validated = checks["platform"]["status"] == "pass" and checks["api"]["status"] == "pass"
    return {
        "loongarch_validated": loongarch_validated,
        "platform": {
            "python": sys.version.split()[0],
            "platform": platform_text,
            "machine": machine,
            "loongarch_like": loongarch_like,
            "sqlite": sqlite3.sqlite_version,
        },
        "checks": checks,
        "modules": modules,
        "database": db,
        "routes": routes,
        "providers": providers,
        "api": api,
        "next_steps": [
            "在 LoongArch + 银河麒麟机器运行本脚本。",
            "启动 8051 服务后带默认 API URL 运行，确认 api=pass。",
            "按 docs/DEMO_SCRIPT.md 录屏文本问诊、图片上传、案例审核、图谱更新和评测。",
        ],
    }


def write_markdown_report(result: dict, output_path: Path | str = DEFAULT_REPORT) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LoongArch Acceptance Report",
        "",
        f"loongarch_validated: `{result['loongarch_validated']}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Evidence |",
        "|---|---|---|",
    ]
    for name, check in result["checks"].items():
        evidence = str(check["evidence"]).replace("\n", " ")
        lines.append(f"| `{name}` | `{check['status']}` | {evidence} |")

    lines.extend(["", "## Platform", "", "```json"])
    lines.append(json.dumps(result["platform"], ensure_ascii=False, indent=2))
    lines.append("```")
    lines.extend(["", "## Database", "", "```json"])
    lines.append(json.dumps(result["database"], ensure_ascii=False, indent=2))
    lines.append("```")
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {item}" for item in result["next_steps"])
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a LoongArch target acceptance report.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8051")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = collect_acceptance(api_base_url=args.api_base_url)
    write_markdown_report(result, args.report)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "loongarch_validated": result["loongarch_validated"],
                    "report": str(args.report),
                    "blocked": [
                        name for name, check in result["checks"].items() if check["status"] == "blocked"
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0 if result["loongarch_validated"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
