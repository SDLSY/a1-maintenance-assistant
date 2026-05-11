from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]

INCLUDE_DIRS = (
    "backend",
    "frontend",
    "scripts",
    "tests",
    "docs",
    "materials",
    "config",
    "supabase",
)
INCLUDE_FILES = (
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    ".env.example",
    ".gitignore",
    "render.yaml",
    "runtime.txt",
)
EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
}
EXCLUDED_NAMES = {
    ".env",
    ".env.local",
}
EXCLUDED_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pdf",
    ".pyc",
    ".pyo",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".zip",
}


def is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = set(rel.parts)
    if parts & EXCLUDED_DIRS:
        return True
    if path.name in EXCLUDED_NAMES:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    return False


def data_files() -> list[Path]:
    candidates: list[Path] = [
        ROOT / "data" / "sources" / "public_manual_sources.json",
        ROOT / "data" / "raw" / "manuals" / "README.md",
        ROOT / "data" / "review" / "mechanical_cases_review.csv",
        ROOT / "data" / "review" / "eval_questions_review.csv",
        ROOT / "data" / "image_eval" / "README.md",
        ROOT / "data" / "image_eval" / "fault_image_eval_manifest.csv",
    ]

    manuals_dir = ROOT / "data" / "raw" / "manuals"
    if manuals_dir.exists():
        candidates.extend(path for path in manuals_dir.glob("*.md"))
        candidates.extend(path for path in manuals_dir.rglob("*.source.json"))
    return candidates


def iter_package_files() -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        if not path.exists() or not path.is_file() or is_excluded(path):
            return
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            files.append(path)

    for name in INCLUDE_FILES:
        add(ROOT / name)

    for dirname in INCLUDE_DIRS:
        base = ROOT / dirname
        if base.exists():
            for path in base.rglob("*"):
                add(path)

    for path in data_files():
        add(path)

    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def manifest_text(files: list[Path], timestamp: str) -> str:
    included = "\n".join(f"- `{path.relative_to(ROOT).as_posix()}`" for path in files)
    return f"""# A1 Submission Package Manifest

Generated: {timestamp}

This archive is a license-safe source and documentation package for the A1 maintenance assistant.

## Included

- Application source: `backend/`, `frontend/`
- Scripts, tests, requirements, and environment template
- Documentation under `docs/`
- Public deployment descriptors such as `render.yaml` and `runtime.txt`
- Public-source manifest and PDF sidecar metadata
- Mechanical review CSV templates
- Multimodal image evaluation manifest and status report

## Excluded

- Real secrets: `.env`, `.env.local`
- Runtime databases: `data/*.db`
- Downloaded public PDFs: `data/raw/manuals/public/*.pdf`
- Uploaded media, image evaluation binaries, caches, virtual environments, build output, and zip archives

PDF manuals are not redistributed by this package. The source URLs and license notes are retained in `data/sources/public_manual_sources.json` and `*.source.json` files for traceable re-download and citation.

## File List

{included}
"""


def build_submission_package(output_dir: Path | str | None = None, timestamp: str | None = None) -> Path:
    stamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M")
    target_dir = Path(output_dir) if output_dir is not None else ROOT / "dist"
    target_dir.mkdir(parents=True, exist_ok=True)
    archive = target_dir / f"a1-maintenance-assistant-submission-{stamp}.zip"

    files = iter_package_files()
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as package:
        package.writestr("SUBMISSION_MANIFEST.md", manifest_text(files, stamp))
        for path in files:
            package.write(path, path.relative_to(ROOT).as_posix())

    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a license-safe A1 submission package.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--timestamp", default=None)
    args = parser.parse_args()

    archive = build_submission_package(output_dir=args.output_dir, timestamp=args.timestamp)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
