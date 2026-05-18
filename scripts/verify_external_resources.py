from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "sources" / "external_reference_resources.json"
OUTPUT_JSON = ROOT / "data" / "sources" / "verified_resources.json"
OUTPUT_MD = ROOT / "docs" / "EXTERNAL_RESOURCE_VERIFICATION.md"
USER_AGENT = "A1-MAKG-resource-verifier/0.1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _request(url: str, *, timeout: int = 45) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _download(url: str, target: Path, *, binary: bool = True) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = _request(url)
    except Exception as exc:  # noqa: BLE001
        return {"downloaded": False, "error": str(exc)}
    if binary:
        target.write_bytes(payload)
    else:
        target.write_text(payload.decode("utf-8", errors="ignore"), encoding="utf-8")
    return {"downloaded": True, "bytes": target.stat().st_size, "error": ""}


def _text_from_pdf(path: Path, max_pages: int = 5) -> tuple[int, str, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        return 0, "", f"pypdf unavailable: {exc}"

    try:
        reader = PdfReader(str(path))
        texts = []
        for index, page in enumerate(reader.pages[:max_pages]):
            texts.append(page.extract_text() or "")
        return len(reader.pages), "\n".join(texts), ""
    except Exception as exc:  # noqa: BLE001
        return 0, "", str(exc)


def _render_pdf_sample(path: Path, resource_id: str) -> dict[str, Any]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return {"rendered": False, "reason": "pdftoppm not found"}

    target_dir = ROOT / "data" / "external" / "references" / "official" / "rendered"
    target_dir.mkdir(parents=True, exist_ok=True)
    prefix = target_dir / resource_id
    command = [pdftoppm, "-f", "1", "-l", "1", "-png", "-singlefile", str(path), str(prefix)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return {"rendered": False, "reason": str(exc)}

    output = prefix.with_suffix(".png")
    if not output.exists() or output.stat().st_size < 1024:
        return {"rendered": False, "reason": "rendered output missing or too small"}

    try:
        from PIL import Image, ImageStat

        with Image.open(output) as image:
            stat = ImageStat.Stat(image.convert("L"))
            return {
                "rendered": True,
                "path": str(output.relative_to(ROOT).as_posix()),
                "width": image.width,
                "height": image.height,
                "mean_luma": round(float(stat.mean[0]), 2),
            }
    except Exception as exc:  # noqa: BLE001
        return {"rendered": True, "path": str(output.relative_to(ROOT).as_posix()), "image_error": str(exc)}


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lower]


def _verify_local_pdf(resource: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / resource["local_path"]
    result = {
        "exists": path.exists(),
        "local_path": resource["local_path"],
        "verify_status": "failed",
        "critical": True,
        "checks": {},
    }
    if not path.exists():
        result["error"] = "local PDF missing"
        return result

    pages, text, error = _text_from_pdf(path)
    keywords = resource.get("expected_keywords", [])
    hits = _keyword_hits(text, keywords)
    expected_pages = int(resource.get("expected_pages", 0) or 0)
    render = _render_pdf_sample(path, resource["id"])
    ok = not error and pages == expected_pages and len(hits) >= min(4, len(keywords)) and bool(render.get("rendered"))
    result.update(
        {
            "verify_status": "verified" if ok else "failed",
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
            "checks": {
                "pages": pages,
                "expected_pages": expected_pages,
                "keyword_hits": hits,
                "keyword_hit_count": len(hits),
                "extract_error": error,
                "render": render,
            },
        }
    )
    return result


def _repo_full_name(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"not a GitHub repo URL: {url}")
    return "/".join(parts[:2])


def _github_api_json(path: str) -> dict[str, Any]:
    return json.loads(_request(f"https://api.github.com/{path}").decode("utf-8"))


def _download_raw_github(full_name: str, branch: str, names: list[str], target_dir: Path) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        raw_url = f"https://raw.githubusercontent.com/{full_name}/{branch}/{name}"
        target = target_dir / name.replace("/", "_")
        status = _download(raw_url, target, binary=False)
        if status["downloaded"] and target.stat().st_size > 20:
            return {"ok": True, "path": str(target.relative_to(ROOT).as_posix()), "name": name}
    return {"ok": False, "error": "none of the candidate files downloaded"}


def _verify_github(resource: dict[str, Any], download: bool) -> dict[str, Any]:
    target_dir = ROOT / resource["local_path"]
    result = {
        "verify_status": "failed",
        "critical": False,
        "local_path": resource["local_path"],
        "checks": {},
    }
    try:
        full_name = _repo_full_name(resource["source_url"])
        repo = _github_api_json(f"repos/{full_name}")
    except Exception as exc:  # noqa: BLE001
        result["error"] = str(exc)
        return result

    branch = repo.get("default_branch") or "main"
    target_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "full_name": repo.get("full_name"),
        "description": repo.get("description", ""),
        "default_branch": branch,
        "html_url": repo.get("html_url"),
        "pushed_at": repo.get("pushed_at"),
        "stargazers_count": repo.get("stargazers_count"),
        "license": (repo.get("license") or {}).get("spdx_id", ""),
    }
    (target_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    readme_result = _download_raw_github(
        full_name,
        branch,
        ["README.md", "README.MD", "readme.md", "README.rst"],
        target_dir,
    ) if download else {"ok": (target_dir / "README.md").exists()}
    license_result = _download_raw_github(
        full_name,
        branch,
        ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"],
        target_dir,
    ) if download else {"ok": any((target_dir / name).exists() for name in ["LICENSE", "LICENSE.md", "LICENSE.txt"])}

    readme_text = ""
    if readme_result.get("ok") and readme_result.get("path"):
        readme_text = (ROOT / readme_result["path"]).read_text(encoding="utf-8", errors="ignore")
    elif (target_dir / "README.md").exists():
        readme_text = (target_dir / "README.md").read_text(encoding="utf-8", errors="ignore")

    hits = _keyword_hits(" ".join([metadata["full_name"] or "", metadata["description"], readme_text]), resource.get("expected_keywords", []))
    ok = metadata["full_name"] == resource["title"] and bool(readme_result.get("ok")) and len(hits) >= 2
    result.update(
        {
            "verify_status": "verified" if ok else "blocked",
            "sha256": _sha256(ROOT / readme_result["path"]) if readme_result.get("path") else "",
            "checks": {
                "metadata": metadata,
                "readme": readme_result,
                "license_file": license_result,
                "keyword_hits": hits,
            },
        }
    )
    return result


def _verify_downloaded_file(resource: dict[str, Any], target: Path) -> dict[str, Any]:
    suffix = target.suffix.lower()
    if suffix == ".pdf":
        pages, text, error = _text_from_pdf(target)
        hits = _keyword_hits(text, resource.get("expected_keywords", []))
        ok = not error and pages > 0 and len(hits) >= 2
        return {
            "ok": ok,
            "pages": pages,
            "keyword_hits": hits,
            "extract_error": error,
            "content_type": mimetypes.guess_type(str(target))[0] or "application/pdf",
        }
    text = target.read_text(encoding="utf-8", errors="ignore")
    hits = _keyword_hits(text, resource.get("expected_keywords", []))
    return {"ok": len(hits) >= 2, "keyword_hits": hits, "content_type": mimetypes.guess_type(str(target))[0] or "text/html"}


def _verify_page_or_paper(resource: dict[str, Any], download: bool) -> dict[str, Any]:
    target = ROOT / resource["local_path"]
    url = resource.get("download_url") or resource["source_url"]
    result = {
        "verify_status": "failed",
        "critical": False,
        "local_path": resource["local_path"],
        "checks": {},
    }
    if download or not target.exists():
        binary = target.suffix.lower() == ".pdf"
        status = _download(url, target, binary=binary)
        if not status["downloaded"]:
            result["verify_status"] = "blocked"
            result["error"] = status["error"]
            return result

    if not target.exists():
        result["verify_status"] = "blocked"
        result["error"] = "target missing after download"
        return result

    file_check = _verify_downloaded_file(resource, target)
    result.update(
        {
            "verify_status": "verified" if file_check["ok"] else "blocked",
            "sha256": _sha256(target),
            "size_bytes": target.stat().st_size,
            "checks": file_check,
        }
    )
    return result


def verify_resource(resource: dict[str, Any], *, download: bool) -> dict[str, Any]:
    base = {
        "id": resource["id"],
        "type": resource["type"],
        "title": resource["title"],
        "source_url": resource["source_url"],
        "usage": resource.get("usage", ""),
        "license": resource.get("license", ""),
        "verified_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
    if resource["type"] == "official_sample_manual":
        details = _verify_local_pdf(resource)
    elif resource["type"] == "github_project":
        details = _verify_github(resource, download=download)
    else:
        details = _verify_page_or_paper(resource, download=download)
    return {**base, **details}


def build_markdown(report: dict[str, Any]) -> str:
    rows = []
    for item in report["resources"]:
        rows.append(
            f"| {item['id']} | {item['type']} | {item['verify_status']} | "
            f"{', '.join(item.get('checks', {}).get('keyword_hits', [])) or '-'} |"
        )
    return "\n".join(
        [
            "# External Resource Verification",
            "",
            f"Generated: {report['generated_at']}",
            "",
            f"- Total: {report['summary']['total']}",
            f"- Verified: {report['summary']['verified']}",
            f"- Blocked: {report['summary']['blocked']}",
            f"- Failed: {report['summary']['failed']}",
            f"- Critical failures: {report['summary']['critical_failures']}",
            "",
            "| Resource | Type | Status | Keyword hits |",
            "|---|---|---|---|",
            *rows,
            "",
            "Notes:",
            "- GitHub references store metadata, README, and LICENSE only; third-party source code is not copied.",
            "- PDFs and article pages are retained only when their content matches expected titles or keywords.",
            "- The official sample PDF is a local contest resource and should not be redistributed unless rules allow it.",
        ]
    )


def run(download: bool = True, ids: set[str] | None = None) -> dict[str, Any]:
    manifest = _read_json(MANIFEST)
    resources = manifest["resources"]
    if ids:
        resources = [item for item in resources if item["id"] in ids]
    results = [verify_resource(resource, download=download) for resource in resources]
    summary = {
        "total": len(results),
        "verified": sum(1 for item in results if item["verify_status"] == "verified"),
        "blocked": sum(1 for item in results if item["verify_status"] == "blocked"),
        "failed": sum(1 for item in results if item["verify_status"] == "failed"),
        "critical_failures": [
            item["id"]
            for item in results
            if item.get("critical") and item["verify_status"] != "verified"
        ],
    }
    report = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "manifest": str(MANIFEST.relative_to(ROOT).as_posix()),
        "summary": summary,
        "resources": results,
    }
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(build_markdown(report), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and verify A1-MAKG external reference resources.")
    parser.add_argument("--no-download", action="store_true", help="Verify existing local files without downloading.")
    parser.add_argument("--id", action="append", default=[], help="Verify only one resource id. Can be repeated.")
    args = parser.parse_args()

    report = run(download=not args.no_download, ids=set(args.id) or None)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 1 if report["summary"]["critical_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
