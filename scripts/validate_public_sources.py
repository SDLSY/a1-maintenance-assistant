from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "sources" / "public_manual_sources.json"
USER_AGENT = "A1-maintenance-assistant-source-check/0.1"


def load_sources() -> list[dict]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return payload["sources"]


def probe_url(url: str) -> dict:
    headers = {"User-Agent": USER_AGENT}
    for method in ("HEAD", "GET"):
        request_headers = dict(headers)
        if method == "GET":
            request_headers["Range"] = "bytes=0-2047"
        request = urllib.request.Request(url, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                if method == "GET":
                    response.read(2048)
                return {
                    "ok": 200 <= response.status < 400,
                    "status": response.status,
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": response.headers.get("content-length", ""),
                    "method": method,
                    "error": "",
                }
        except urllib.error.HTTPError as exc:
            if method == "HEAD":
                continue
            return {
                "ok": False,
                "status": exc.code,
                "content_type": exc.headers.get("content-type", ""),
                "content_length": exc.headers.get("content-length", ""),
                "method": method,
                "error": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            if method == "HEAD":
                continue
            return {
                "ok": False,
                "status": 0,
                "content_type": "",
                "content_length": "",
                "method": method,
                "error": str(exc),
            }
    return {"ok": False, "status": 0, "content_type": "", "content_length": "", "method": "", "error": "unreachable"}


def main() -> int:
    sources = [source for source in load_sources() if source.get("active", True)]
    results = []
    for source in sources:
        result = {"id": source["id"], "equipment": source["equipment"], **probe_url(source["source_url"])}
        results.append(result)
        marker = "OK" if result["ok"] else "FAIL"
        print(f"{marker} {result['id']} {result['status']} {result['content_type']}")

    ok_count = sum(1 for item in results if item["ok"])
    equipment = sorted({source["equipment"] for source in sources})
    summary = {"sources": len(sources), "reachable": ok_count, "equipment": equipment}
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if ok_count >= 8 and set(equipment) >= {"motor", "pump", "bearing"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
