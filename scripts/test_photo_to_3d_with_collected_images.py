from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
COMMONS_MANIFEST = ROOT / "data" / "image_eval" / "commons_image_sources.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _load_commons_sources() -> list[dict[str, Any]]:
    payload = json.loads(COMMONS_MANIFEST.read_text(encoding="utf-8"))
    return list(payload.get("images", []))


def _copy_or_download(source: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    local = ROOT / source["local_path"]
    suffix = local.suffix or ".jpg"
    target = target_dir / f"{source['id']}{suffix}"
    if local.exists():
        shutil.copy2(local, target)
    else:
        urlretrieve(source.get("original_url") or source["download_url"], target)
    with Image.open(target) as image:
        width, height = image.size
    return {
        "id": source["id"],
        "title": source.get("title", ""),
        "equipment": source.get("equipment", ""),
        "fault_type": source.get("fault_type", ""),
        "path": str(target),
        "width": width,
        "height": height,
        "bytes": target.stat().st_size,
        "sha256": _sha256(target),
        "source_page": source.get("commons_page_url", ""),
        "license": source.get("license_short_name", ""),
        "license_url": source.get("license_url", ""),
    }


def _create_controlled_views(base_image: Path, target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(base_image) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        width, height = image.size
        side = min(width, height)
        left = max(0, (width - side) // 2)
        top = max(0, (height - side) // 2)
        square = image.crop((left, top, left + side, top + side)).resize((900, 900))
        outputs: list[Path] = []
        for index in range(12):
            angle = (index - 5.5) * 3.0
            scale_margin = 18 + (index % 4) * 14
            view = square.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=(238, 243, 245))
            view = view.crop((scale_margin, scale_margin, 900 - scale_margin, 900 - scale_margin)).resize((900, 900))
            target = target_dir / f"controlled-view-{index + 1:02d}.jpg"
            view.save(target, quality=92)
            outputs.append(target)
    return outputs


def _configure_test_app(output_dir: Path):
    upload_dir = output_dir / "api_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    os.environ["ACTIVE_MODEL_PROVIDER"] = "local"
    os.environ["TEXT_AGENT_PROVIDER"] = "local"
    os.environ["VISION_AGENT_PROVIDER"] = "local"
    os.environ["EMBEDDING_AGENT_PROVIDER"] = "local"
    os.environ["COMPLIANCE_AGENT_PROVIDER"] = "local"
    os.environ["KNOWLEDGE_AGENT_PROVIDER"] = "local"
    os.environ["A1_DB_PATH"] = str(output_dir / "photo-to-3d-test.db")
    os.environ["A1_UPLOAD_DIR"] = str(upload_dir)
    sys.path.insert(0, str(ROOT))
    from fastapi.testclient import TestClient

    from backend.app.database import reset_demo_db
    from backend.app.main import app

    reset_demo_db()
    return TestClient(app)


def _post_files(client, url: str, paths: list[Path]) -> dict[str, Any]:
    handles = []
    try:
        files = []
        for path in paths:
            handle = path.open("rb")
            handles.append(handle)
            files.append(("files", (path.name, handle, "image/jpeg")))
        response = client.post(url, files=files)
        response.raise_for_status()
        return response.json()
    finally:
        for handle in handles:
            handle.close()


def _upload_one_photo(client, path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        response = client.post(
            "/api/upload-image",
            files={"file": (path.name, handle, "image/jpeg")},
        )
    response.raise_for_status()
    uploaded = response.json()
    one_photo = client.post(
        "/api/3d/reconstruct/one-photo",
        json={"visual_asset_id": uploaded["visual_asset_id"], "provider": "cached_demo"},
    )
    one_photo.raise_for_status()
    return {"upload": uploaded, "job": one_photo.json()["job"]}


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    collected_dir = output_dir / "public_collected_images"
    public_bearing_dir = output_dir / "public_bearing_set"
    controlled_dir = output_dir / "controlled_multiview_from_public_image"
    offline_dir = output_dir / "offline_package"

    sources = _load_commons_sources()
    bearing_sources = [item for item in sources if str(item.get("id", "")).startswith("IMG-BEARING")]
    if len(bearing_sources) < 10:
        raise RuntimeError("Need at least 10 bearing images in the Commons manifest")
    one_photo_source = next((item for item in bearing_sources if item["id"] == "IMG-BEARING-010"), bearing_sources[0])
    one_photo_asset = _copy_or_download(one_photo_source, collected_dir)

    public_multi_assets = [_copy_or_download(item, public_bearing_dir) for item in bearing_sources[:10]]
    controlled_paths = _create_controlled_views(Path(one_photo_asset["path"]), controlled_dir)

    client = _configure_test_app(output_dir)
    one_photo_result = _upload_one_photo(client, Path(one_photo_asset["path"]))
    public_multi_result = _post_files(
        client,
        "/api/3d/reconstruct/multi-photo?equipment=bearing",
        [Path(item["path"]) for item in public_multi_assets],
    )
    controlled_multi_result = _post_files(
        client,
        "/api/3d/reconstruct/multi-photo?equipment=bearing",
        controlled_paths,
    )

    package = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_3d_reconstruction.py"),
            "--job-id",
            "collected-photo-to-3d",
            "--input-dir",
            str(controlled_dir),
            "--output-dir",
            str(offline_dir),
            "--backend",
            "dry-run",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if package.returncode != 0:
        raise RuntimeError(package.stderr or package.stdout)
    plan = json.loads((offline_dir / "photo_to_3d_plan.json").read_text(encoding="utf-8"))

    report = {
        "schema_version": "1.0",
        "output_dir": str(output_dir),
        "public_sources": {
            "provider": "Wikimedia Commons",
            "source_manifest": str(COMMONS_MANIFEST),
            "total_collected": 1 + len(public_multi_assets),
            "one_photo_source": one_photo_asset,
            "public_multi_photo_sources": public_multi_assets,
        },
        "one_photo": {
            "purpose": "真实公开图片到标准 3D 模型部件定位",
            **one_photo_result,
        },
        "public_multi_photo": {
            "purpose": "公开轴承图片集合的负向质量门测试；这些图片不是同一设备多角度采集",
            **public_multi_result,
        },
        "controlled_multi_photo": {
            "purpose": "从公开图片生成的受控增强视图，用于验证 12 图质量门和离线任务包链路，不代表真实摄影测量成功",
            "input_images": [str(path) for path in controlled_paths],
            "job": controlled_multi_result["job"],
        },
        "offline_package": {
            "path": str(offline_dir),
            "plan": plan,
        },
        "conclusion": {
            "one_photo_component_alignment_tested": True,
            "multi_photo_quality_gate_tested": True,
            "offline_task_package_tested": True,
            "true_3d_reconstruction_completed": False,
            "risk_statement": "当前测试证明 photo-to-3D 的定位包、质量门和离线任务包可运行；真实 3D 重建未完成，结果不作为尺寸测量或安全放行依据。",
        },
    }
    (output_dir / "photo_to_3d_collected_test_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "PHOTO_TO_3D_COLLECTED_TEST_REPORT.md").write_text(_markdown_report(report), encoding="utf-8")
    return report


def _markdown_report(report: dict[str, Any]) -> str:
    one_job = report["one_photo"]["job"]
    public_job = report["public_multi_photo"]["job"]
    controlled_job = report["controlled_multi_photo"]["job"]
    return "\n".join(
        [
            "# Photo-to-3D Collected Image Test Report",
            "",
            "## 数据来源",
            "",
            f"- Provider: {report['public_sources']['provider']}",
            f"- Collected images: {report['public_sources']['total_collected']}",
            f"- One-photo source: {report['public_sources']['one_photo_source']['source_page']}",
            "",
            "## one-photo",
            "",
            f"- Status: `{one_job['status']}`",
            f"- Result type: `{one_job['result_type']}`",
            f"- True 3D generation: `{one_job['log']['is_true_3d_generation']}`",
            f"- Highlighted components: `{len(one_job['log']['highlighted_components'])}`",
            "",
            "## multi-photo",
            "",
            f"- Public image set status: `{public_job['status']}`",
            f"- Public quality issues: `{public_job['log']['quality_gate']['issues']}`",
            f"- Controlled 12-view status: `{controlled_job['status']}`",
            f"- Controlled result type: `{controlled_job['result_type']}`",
            "",
            "## Offline package",
            "",
            f"- Package path: `{report['offline_package']['path']}`",
            f"- Plan status: `{report['offline_package']['plan']['status']}`",
            f"- Planned backends: `{', '.join(report['offline_package']['plan']['planned_backends'])}`",
            "",
            "## 结论",
            "",
            "- one-photo 定位包已跑通。",
            "- multi-photo 质量门和离线任务包已跑通。",
            "- 真实 3D 重建未完成。",
            f"- {report['conclusion']['risk_statement']}",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect traceable images and test the photo-to-3D workflow.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "data" / "photo_to_3d_eval"),
        help="Directory for collected images and reports.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(Path(args.output_dir).resolve())
    print(json.dumps({"report": str(Path(args.output_dir) / "photo_to_3d_collected_test_report.json"), "conclusion": report["conclusion"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
