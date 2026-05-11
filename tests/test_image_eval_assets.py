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

    assert "data/image_eval/README.md" in names
    assert "data/image_eval/fault_image_eval_manifest.csv" in names
    assert "docs/IMAGE_EVAL_STATUS.md" in names
    assert not any(name.startswith("data/image_eval/images/") for name in names)


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
