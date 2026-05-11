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


def test_final_defense_deck_is_18_page_image_only(tmp_path: Path) -> None:
    from scripts.build_defense_image_only_final import build_final_image_only_deck

    output = build_final_image_only_deck(
        output_path=tmp_path / "a1-final-image-only.pptx",
        slide_output_dir=tmp_path / "slides",
    )

    with zipfile.ZipFile(output) as archive:
        slide_names = [
            name
            for name in archive.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        ]
        media = [name for name in archive.namelist() if name.startswith("ppt/media/")]
        slide_xml = [archive.read(name).decode("utf-8", errors="ignore") for name in slide_names]

    assert len(slide_names) == 18
    assert len(media) == len(slide_names)
    assert all("<p:pic>" in xml for xml in slide_xml)
    assert not any("<a:t>" in xml for xml in slide_xml)
    assert (tmp_path / "slides" / "slide06_data_evidence.png").exists()
    assert (tmp_path / "slides" / "slide18_deployment_validation.png").exists()


def test_defense_material_verifier_tracks_final_image_only_deck() -> None:
    from scripts.verify_defense_materials import build_report

    report = build_report()

    assert report["checks"]["final_image_only_deck_shape"] is True
    assert report["checks"]["final_image_only_xml_has_no_text"] is True
    assert report["checks"]["final_slide_images_exist"] is True
    assert report["final_image_only_ppt"]["slides"] == 18
    assert report["final_image_only_ppt"]["text_shapes"] == 0
