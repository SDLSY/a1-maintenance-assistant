from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_full_slide_prompt_catalog_is_complete() -> None:
    catalog_path = ROOT / "materials" / "full_slide_prompts.json"

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    assert catalog["deck_mode"] == "full-image-slides"
    assert len(catalog["slides"]) >= 12
    for index, item in enumerate(catalog["slides"], start=1):
        assert item["slide"] == index
        assert item["model"] == "gpt-image-2"
        assert item["size"] == "1536x864"
        assert item["quality"] in {"medium", "high"}
        assert "完整16:9中文PPT页面" in item["prompt"]
        assert (ROOT / "materials" / "full_slides" / item["file"]).exists()


def test_generated_ppt_is_full_image_deck(tmp_path: Path) -> None:
    from scripts.build_ppt import build_presentation

    output = build_presentation(tmp_path / "full-image-deck.pptx")

    with zipfile.ZipFile(output) as archive:
        slide_names = [
            name
            for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ]
        media = [name for name in archive.namelist() if name.startswith("ppt/media/")]
        slide_xml = [archive.read(name).decode("utf-8", errors="ignore") for name in slide_names]

    assert len(slide_names) >= 12
    assert len(media) == len(slide_names)
    assert all("<p:pic>" in xml for xml in slide_xml)
    assert not any("<a:t>" in xml for xml in slide_xml)
