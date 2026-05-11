from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_image_eval_manifest_summarizes_required_assets(tmp_path: Path) -> None:
    from scripts.image_eval_status import (
        DEFAULT_MANIFEST,
        REQUIRED_IMAGES,
        summarize_manifest,
        write_markdown_report,
    )

    result = summarize_manifest(DEFAULT_MANIFEST)

    assert result["exists"] is True
    assert result["required_images"] == REQUIRED_IMAGES == 30
    assert result["total"] >= REQUIRED_IMAGES
    assert result["available_images"] + result["missing_images"] == result["total"]
    assert {"motor", "pump", "bearing"} <= set(result["by_equipment"])
    assert result["ready"] == (
        result["available_images"] >= REQUIRED_IMAGES
        and result["approved_images"] >= REQUIRED_IMAGES
    )
    assert result["missing_paths"] or result["ready"]

    report = write_markdown_report(result, tmp_path / "image-eval-status.md")
    text = report.read_text(encoding="utf-8")
    assert "Multimodal Image Evaluation Status" in text
    assert "required_images" in text
    assert "missing_paths" in text


def test_submission_package_includes_image_eval_manifest(tmp_path: Path) -> None:
    from scripts.build_submission_package import build_submission_package

    archive = build_submission_package(output_dir=tmp_path, timestamp="image-eval")
    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())
        image_assets = [name for name in names if name.startswith("data/image_eval/images/")]
        image_asset_size = sum(package.getinfo(name).file_size for name in image_assets)

    assert "data/image_eval/README.md" in names
    assert "data/image_eval/fault_image_eval_manifest.csv" in names
    assert "data/image_eval/commons_image_sources.json" in names
    assert "docs/IMAGE_EVAL_STATUS.md" in names
    assert len(image_assets) >= 30
    assert image_asset_size <= 40 * 1024 * 1024
    assert not any(name.startswith("data/uploads/") for name in names)


def test_commons_image_sources_cover_manifest() -> None:
    import json
    from scripts.image_eval_status import DEFAULT_MANIFEST, summarize_manifest

    sources_path = ROOT / "data" / "image_eval" / "commons_image_sources.json"
    assert sources_path.exists()
    payload = json.loads(sources_path.read_text(encoding="utf-8"))
    assert payload["provider"] == "Wikimedia Commons"
    assert len(payload["images"]) >= 30
    source_by_id = {item["id"]: item for item in payload["images"]}

    result = summarize_manifest(DEFAULT_MANIFEST)
    assert result["ready"] is True
    assert result["available_images"] >= 30
    assert result["approved_images"] >= 30

    for item_id, item in source_by_id.items():
        assert item_id
        assert item["commons_page_url"].startswith("https://commons.wikimedia.org/wiki/File:")
        assert item["license_short_name"]
        assert item["local_path"].startswith("data/image_eval/images/")
        assert item["local_size_bytes"] <= 4 * 1024 * 1024
        assert item["local_width"] <= 1600
        assert item["local_height"] <= 1600


def test_image_eval_rejects_known_non_photo_placeholders() -> None:
    import csv
    import json

    manifest_path = ROOT / "data" / "image_eval" / "fault_image_eval_manifest.csv"
    rows = list(csv.DictReader(manifest_path.open("r", newline="", encoding="utf-8-sig")))
    manifest_paths = {row["image_path"] for row in rows}
    source_payload = json.loads((ROOT / "data" / "image_eval" / "commons_image_sources.json").read_text(encoding="utf-8"))
    titles = {item["title"] for item in source_payload["images"]}

    assert "data/image_eval/images/motor_ball_bearing_diagram_01.png" not in manifest_paths
    assert "data/image_eval/images/bearing_badly_worn_taper_01.jpg" not in manifest_paths
    assert "File:Ball Bearing electric motor.png" not in titles
    assert "File:Badly-worn taper roller bearing (Montagu, Cars and Motor-Cycles, 1928).jpg" not in titles
    assert "File:Mechanical Seals by American Seal and Packing.jpg" not in titles


def test_image_eval_status_api_and_frontend_gate() -> None:
    from backend.app.main import app

    response = TestClient(app).get("/api/image-eval/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["required_images"] == 30
    assert "missing_paths" in payload

    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "image-eval-strip" in index
    assert "imageEvalStatus" in app_js
    assert "/api/image-eval/status" in app_js
