from __future__ import annotations

import argparse
import http.client
import json
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "sources" / "public_manual_sources.json"
TARGET_DIR = ROOT / "data" / "raw" / "manuals" / "public"
USER_AGENT = "A1-maintenance-assistant-source-download/0.1"


def load_sources() -> list[dict]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return payload["sources"]


def selected_sources(ids: set[str], required_only: bool) -> list[dict]:
    sources = [source for source in load_sources() if source.get("active", True)]
    if ids:
        sources = [source for source in sources if source["id"] in ids]
    if required_only:
        sources = [source for source in sources if source.get("priority") == "required"]
    return sources


def _download_bytes(url: str, target: Path) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    tmp = target.with_suffix(target.suffix + ".tmp")
    with urllib.request.urlopen(request, timeout=120) as response, tmp.open("wb") as handle:
        while True:
            try:
                chunk = response.read(1024 * 512)
            except http.client.IncompleteRead as exc:
                chunk = exc.partial
            if not chunk:
                break
            handle.write(chunk)
    tmp.replace(target)
    if target.suffix.lower() == ".pdf" and b"%%EOF" not in target.read_bytes()[-4096:]:
        raise RuntimeError("downloaded PDF is missing EOF marker")
    return target.stat().st_size


def download(source: dict, force: bool = False, retries: int = 2) -> dict:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    target = TARGET_DIR / source["target_filename"]
    sidecar = target.with_name(f"{target.name}.source.json")
    if target.exists() and not force:
        return {"id": source["id"], "path": str(target), "status": "exists"}

    last_error = ""
    for attempt in range(retries + 1):
        try:
            size = _download_bytes(source["source_url"], target)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if attempt >= retries:
                return {"id": source["id"], "path": str(target), "status": "failed", "error": last_error}

    sidecar_payload = {
        "id": source["id"],
        "title": source["title"],
        "equipment": source["equipment"],
        "publisher": source["publisher"],
        "source_url": source["source_url"],
        "license": source["license"],
        "version": source.get("version", ""),
        "downloaded_at": datetime.utcnow().isoformat(timespec="seconds"),
        "redistribution": "Do not commit or publish this PDF without checking the rights holder's terms.",
    }
    sidecar.write_text(json.dumps(sidecar_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"id": source["id"], "path": str(target), "bytes": size, "status": "downloaded"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public manual PDFs listed in data/sources.")
    parser.add_argument("--id", action="append", default=[], help="Download only the given source id. Can be repeated.")
    parser.add_argument("--required-only", action="store_true", help="Download only sources marked as required.")
    parser.add_argument("--force", action="store_true", help="Overwrite already downloaded files.")
    parser.add_argument("--dry-run", action="store_true", help="Print selected sources without downloading.")
    args = parser.parse_args()

    sources = selected_sources(set(args.id), args.required_only)
    if args.dry_run:
        for source in sources:
            print(f"{source['id']}\t{source['equipment']}\t{source['source_url']}")
        return 0

    results = [download(source, force=args.force) for source in sources]
    print(json.dumps({"target_dir": str(TARGET_DIR), "results": results}, ensure_ascii=False, indent=2))
    return 1 if any(result["status"] == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
