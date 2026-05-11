from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
DEFAULT_OUTPUT_DIR = ROOT / "dist" / "cloudflare-site"


def _clean_output(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / "static").mkdir(parents=True, exist_ok=True)


def _normalized_api_base_url(api_base_url: str) -> str:
    return api_base_url.strip().rstrip("/")


def prepare_cloudflare_site(
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    api_base_url: str = "",
) -> Path:
    target = Path(output_dir)
    _clean_output(target)

    shutil.copy2(FRONTEND_DIR / "index.html", target / "index.html")
    for name in ("app.js", "styles.css"):
        shutil.copy2(FRONTEND_DIR / name, target / "static" / name)
    shutil.copytree(FRONTEND_DIR / "vendor", target / "static" / "vendor")

    api_base = _normalized_api_base_url(api_base_url)
    config = f"window.A1_API_BASE_URL = {json.dumps(api_base, ensure_ascii=False)};\n"
    (target / "static" / "config.js").write_text(config, encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare static assets for Cloudflare Pages.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--api-base-url", default="")
    args = parser.parse_args()

    output = prepare_cloudflare_site(output_dir=args.output_dir, api_base_url=args.api_base_url)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
