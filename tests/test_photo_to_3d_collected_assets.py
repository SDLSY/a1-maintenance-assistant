from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_photo_to_3d_collected_image_script_runs(tmp_path: Path) -> None:
    output_dir = tmp_path / "photo_to_3d_eval"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "test_photo_to_3d_with_collected_images.py"),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report_path = output_dir / "photo_to_3d_collected_test_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["public_sources"]["provider"] == "Wikimedia Commons"
    assert report["public_sources"]["total_collected"] >= 10
    assert report["one_photo"]["job"]["status"] == "completed_cached"
    assert report["one_photo"]["job"]["log"]["is_true_3d_generation"] is False
    assert Path(report["one_photo"]["upload"]["stored_path"]).is_relative_to(output_dir / "api_uploads")
    assert report["public_multi_photo"]["job"]["status"] == "blocked_quality_gate"
    assert report["public_multi_photo"]["job"]["log"]["quality_gate"]["passed"] is False
    assert report["controlled_multi_photo"]["job"]["status"] == "ready_for_offline_reconstruction"
    assert Path(report["controlled_multi_photo"]["job"]["result_path"]).is_relative_to(
        output_dir / "api_uploads"
    )
    assert report["offline_package"]["plan"]["status"] == "planned"
    assert report["offline_package"]["plan"]["true_3d_generation"] is False
    assert report["conclusion"]["true_3d_reconstruction_completed"] is False
    assert "不作为尺寸测量或安全放行依据" in report["conclusion"]["risk_statement"]

    markdown = output_dir / "PHOTO_TO_3D_COLLECTED_TEST_REPORT.md"
    assert markdown.exists()
    text = markdown.read_text(encoding="utf-8")
    assert "one-photo" in text
    assert "multi-photo" in text
    assert "真实 3D 重建未完成" in text
