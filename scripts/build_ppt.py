from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "materials" / "A1-maintenance-assistant-defense.pptx"
PROMPT_CATALOG = ROOT / "materials" / "full_slide_prompts.json"
FULL_SLIDE_DIR = ROOT / "materials" / "full_slides"


def _load_slide_files() -> list[Path]:
    if not PROMPT_CATALOG.exists():
        raise FileNotFoundError(f"Missing full-slide prompt catalog: {PROMPT_CATALOG}")

    catalog = json.loads(PROMPT_CATALOG.read_text(encoding="utf-8"))
    if catalog.get("deck_mode") != "full-image-slides":
        raise ValueError("full_slide_prompts.json must use deck_mode=full-image-slides")

    slide_files: list[Path] = []
    for item in sorted(catalog["slides"], key=lambda row: row["slide"]):
        path = FULL_SLIDE_DIR / item["file"]
        if not path.exists():
            raise FileNotFoundError(f"Missing generated full-slide image: {path}")
        slide_files.append(path)
    return slide_files


def build_presentation(output_path: Path | str = DEFAULT_OUTPUT) -> Path:
    try:
        from pptx import Presentation
        from pptx.util import Inches
    except ModuleNotFoundError as exc:  # pragma: no cover - developer setup hint.
        raise SystemExit("python-pptx is required: .\\.venv\\Scripts\\python.exe -m pip install python-pptx") from exc

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    for image_path in _load_slide_files():
        slide = prs.slides.add_slide(blank)
        slide.shapes.add_picture(
            str(image_path),
            Inches(0),
            Inches(0),
            width=prs.slide_width,
            height=prs.slide_height,
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the full-image A1 defense PPT.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = build_presentation(args.output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
