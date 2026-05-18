from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import urlretrieve

from PIL import Image, ImageOps
from PIL import ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "photo_to_3d_real" / "strecha_fountain_pycolmap"

DATASETS: dict[str, dict[str, Any]] = {
    "strecha_fountain": {
        "title": "Strecha Fountain multi-view dataset",
        "source_url": "https://cvg-data.inf.ethz.ch/local-feature-evaluation-schoenberger2017/Strecha-Fountain.zip",
        "reference_url": "https://github.com/colmap/pycolmap/blob/master/example.py",
        "image_dir": "Fountain/images",
        "expected_min_bytes": 200_000_000,
        "license_note": "Public research dataset used by PyCOLMAP example; keep source attribution in reports.",
        "usage": "Real multi-view SfM reconstruction smoke test.",
    }
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)

    def _progress(blocks: int, block_size: int, total_size: int) -> None:
        if total_size <= 0:
            return
        done = min(blocks * block_size, total_size)
        pct = done * 100 / total_size
        if blocks % 64 == 0:
            print(f"download {pct:5.1f}% {done / 1024 / 1024:7.1f}MB/{total_size / 1024 / 1024:7.1f}MB")

    urlretrieve(url, target, _progress)


def _ensure_dataset(dataset: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    dataset_dir = output_dir / "dataset"
    zip_path = dataset_dir / Path(dataset["source_url"]).name
    image_dir = dataset_dir / dataset["image_dir"]
    if not image_dir.exists():
        if not zip_path.exists():
            _download(dataset["source_url"], zip_path)
        if zip_path.stat().st_size < int(dataset["expected_min_bytes"]):
            raise RuntimeError(f"Dataset archive is too small: {zip_path} ({zip_path.stat().st_size} bytes)")
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(dataset_dir)
    raw_images = sorted(path for path in image_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if len(raw_images) < 8:
        raise RuntimeError(f"Expected a real multi-view image set, got {len(raw_images)} images in {image_dir}")

    prepared_dir = output_dir / "prepared_images"
    prepared_dir.mkdir(parents=True, exist_ok=True)
    prepared_images: list[Path] = []
    for index, raw_image in enumerate(raw_images):
        target = prepared_dir / f"{index:04d}.jpg"
        if not target.exists():
            with Image.open(raw_image) as image:
                rgb = ImageOps.exif_transpose(image).convert("RGB")
                rgb.save(target, quality=95, optimize=True)
        prepared_images.append(target)
    return {
        "zip_path": str(zip_path),
        "zip_bytes": zip_path.stat().st_size if zip_path.exists() else 0,
        "zip_sha256": _sha256(zip_path) if zip_path.exists() else "",
        "raw_image_dir": str(image_dir),
        "raw_image_count": len(raw_images),
        "raw_images": [path.name for path in raw_images],
        "image_dir": str(prepared_dir),
        "image_count": len(prepared_images),
        "images": [path.name for path in prepared_images],
        "preprocess": "raw images converted to 8-bit RGB JPEG for COLMAP bitmap compatibility",
    }


def _ply_vertex_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        for raw in handle:
            line = raw.decode("ascii", errors="ignore").strip()
            if line.startswith("element vertex "):
                return int(line.split()[-1])
            if line == "end_header":
                break
    return 0


def _read_binary_ply_vertices(path: Path) -> list[tuple[float, float, float, int, int, int]]:
    header = b""
    with path.open("rb") as handle:
        while True:
            line = handle.readline()
            if not line:
                return []
            header += line
            if line.strip() == b"end_header":
                break
        header_text = header.decode("ascii", errors="ignore")
        if "format binary_little_endian 1.0" not in header_text:
            return []
        vertex_count = 0
        for line in header_text.splitlines():
            if line.startswith("element vertex "):
                vertex_count = int(line.split()[-1])
                break
        vertices = []
        record = struct.Struct("<fffBBB")
        for _ in range(vertex_count):
            raw = handle.read(record.size)
            if len(raw) != record.size:
                break
            x, y, z, r, g, b = record.unpack(raw)
            vertices.append((x, y, z, r, g, b))
        return vertices


def _render_point_cloud_preview(ply_path: Path, target: Path) -> int:
    vertices = _read_binary_ply_vertices(ply_path)
    if not vertices:
        return 0
    width, height = 1200, 640
    padding = 44
    panel_w = (width - padding * 3) // 2
    panel_h = height - padding * 2
    image = Image.new("RGB", (width, height), (246, 248, 250))
    draw = ImageDraw.Draw(image)
    draw.rectangle((padding, padding, padding + panel_w, padding + panel_h), outline=(180, 190, 198))
    draw.rectangle(
        (padding * 2 + panel_w, padding, padding * 2 + panel_w * 2, padding + panel_h),
        outline=(180, 190, 198),
    )
    draw.text((padding, 16), "Sparse SfM point cloud - XY projection", fill=(31, 42, 55))
    draw.text((padding * 2 + panel_w, 16), "Sparse SfM point cloud - XZ projection", fill=(31, 42, 55))

    def project(axis_a: int, axis_b: int, origin_x: int) -> None:
        values_a = [point[axis_a] for point in vertices]
        values_b = [point[axis_b] for point in vertices]
        min_a, max_a = min(values_a), max(values_a)
        min_b, max_b = min(values_b), max(values_b)
        range_a = max(max_a - min_a, 1e-9)
        range_b = max(max_b - min_b, 1e-9)
        for point in vertices:
            px = origin_x + int((point[axis_a] - min_a) / range_a * (panel_w - 8)) + 4
            py = padding + panel_h - int((point[axis_b] - min_b) / range_b * (panel_h - 8)) - 4
            color = tuple(max(0, min(255, int(c))) for c in point[3:6])
            draw.point((px, py), fill=color)

    project(0, 1, padding)
    project(0, 2, padding * 2 + panel_w)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return len(vertices)


def run_pycolmap_reconstruction(
    *,
    image_dir: Path,
    output_dir: Path,
    work_dir: Path,
    max_image_size: int,
    max_num_features: int,
    min_model_size: int,
) -> dict[str, Any]:
    try:
        import pycolmap
    except ImportError as exc:
        raise RuntimeError("pycolmap is not installed. Install requirements-3d.txt first.") from exc

    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    work_image_dir = work_dir / "images"
    work_image_dir.mkdir(parents=True, exist_ok=True)
    for image in sorted(image_dir.iterdir()):
        if image.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            shutil.copy2(image, work_image_dir / image.name)

    database_path = work_dir / "database.db"
    sfm_dir = work_dir / "sfm"
    work_sparse_dir = sfm_dir / "best_model"
    work_sparse_ply = work_dir / "sparse_points.ply"
    artifact_sfm_dir = output_dir / "sfm"
    artifact_sparse_dir = artifact_sfm_dir / "best_model"
    artifact_sparse_ply = output_dir / "sparse_points.ply"
    artifact_preview = output_dir / "sparse_points_preview.png"
    artifact_database_path = output_dir / "database.db"

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sfm_dir.mkdir(parents=True, exist_ok=True)

    timings: dict[str, float] = {}

    extraction_options = pycolmap.FeatureExtractionOptions()
    extraction_options.max_image_size = max_image_size
    extraction_options.use_gpu = False
    extraction_options.sift.max_num_features = max_num_features

    matching_options = pycolmap.FeatureMatchingOptions()
    matching_options.use_gpu = False

    mapping_options = pycolmap.IncrementalPipelineOptions()
    mapping_options.min_model_size = min_model_size
    mapping_options.multiple_models = True

    start = time.perf_counter()
    pycolmap.extract_features(
        database_path,
        work_image_dir,
        camera_mode=pycolmap.CameraMode.SINGLE,
        extraction_options=extraction_options,
        device=pycolmap.Device.cpu,
    )
    timings["extract_features_sec"] = round(time.perf_counter() - start, 3)

    start = time.perf_counter()
    pycolmap.match_exhaustive(
        database_path,
        matching_options=matching_options,
        device=pycolmap.Device.cpu,
    )
    timings["match_exhaustive_sec"] = round(time.perf_counter() - start, 3)

    start = time.perf_counter()
    reconstructions = pycolmap.incremental_mapping(
        database_path,
        work_image_dir,
        sfm_dir,
        options=mapping_options,
    )
    timings["incremental_mapping_sec"] = round(time.perf_counter() - start, 3)

    if not reconstructions:
        return {
            "ok": False,
            "status": "failed_no_reconstruction",
            "timings": timings,
            "database_path": str(database_path),
            "sfm_dir": str(sfm_dir),
            "work_dir": str(work_dir),
            "models": [],
        }

    best_id, best = max(
        reconstructions.items(),
        key=lambda item: (item[1].num_reg_images(), item[1].num_points3D()),
    )
    work_sparse_dir.mkdir(parents=True, exist_ok=True)
    best.write(work_sparse_dir)
    best.export_PLY(work_sparse_ply)
    shutil.copy2(database_path, artifact_database_path)
    shutil.copytree(work_sparse_dir, artifact_sparse_dir, dirs_exist_ok=True)
    shutil.copy2(work_sparse_ply, artifact_sparse_ply)
    preview_points = _render_point_cloud_preview(artifact_sparse_ply, artifact_preview)

    models = []
    for model_id, rec in sorted(reconstructions.items()):
        models.append(
            {
                "model_id": int(model_id),
                "num_images": int(rec.num_images()),
                "num_registered_images": int(rec.num_reg_images()),
                "num_points3D": int(rec.num_points3D()),
                "num_observations": int(rec.compute_num_observations()),
                "mean_track_length": float(rec.compute_mean_track_length()),
                "mean_observations_per_registered_image": float(rec.compute_mean_observations_per_reg_image()),
                "mean_reprojection_error_px": float(rec.compute_mean_reprojection_error()),
                "summary": rec.summary(),
            }
        )

    return {
        "ok": best.num_reg_images() >= min_model_size and best.num_points3D() > 0,
        "status": "completed_sparse_reconstruction",
        "backend": "pycolmap-sfm",
        "pycolmap_version": pycolmap.__version__,
        "true_3d_generation": True,
        "generation_type": "real_sparse_structure_from_motion",
        "timings": timings,
        "database_path": str(database_path),
        "artifact_database_path": str(artifact_database_path),
        "sfm_dir": str(sfm_dir),
        "work_dir": str(work_dir),
        "best_model_dir": str(artifact_sparse_dir),
        "sparse_point_cloud": str(artifact_sparse_ply),
        "sparse_point_cloud_preview": str(artifact_preview),
        "preview_points": preview_points,
        "sparse_ply_vertex_count": _ply_vertex_count(artifact_sparse_ply),
        "best_model_id": int(best_id),
        "best_num_registered_images": int(best.num_reg_images()),
        "best_num_points3D": int(best.num_points3D()),
        "best_mean_reprojection_error_px": float(best.compute_mean_reprojection_error()),
        "models": models,
        "limitations": [
            "This run produces a sparse SfM point cloud and camera poses, not a dense mesh.",
            "It validates the real reconstruction toolchain but does not yet reconstruct motor/pump/bearing photos.",
            "The output is not metrically calibrated for maintenance dimensions or safety release.",
        ],
    }


def _write_report(report: dict[str, Any], output_dir: Path) -> None:
    json_path = output_dir / "real_photo_to_3d_reconstruction_report.json"
    md_path = output_dir / "REAL_PHOTO_TO_3D_RECONSTRUCTION_REPORT.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    result = report["result"]
    lines = [
        "# Real Photo-to-3D Reconstruction Report",
        "",
        "## Dataset",
        "",
        f"- Title: {report['dataset']['title']}",
        f"- Source: {report['dataset']['source_url']}",
        f"- Images: {report['dataset_verification']['image_count']}",
        f"- Archive SHA256: `{report['dataset_verification']['zip_sha256']}`",
        "",
        "## Reconstruction",
        "",
        f"- Backend: `{result.get('backend', 'pycolmap-sfm')}`",
        f"- Status: `{result['status']}`",
        f"- True 3D generation: `{result.get('true_3d_generation', False)}`",
        f"- Registered images: `{result.get('best_num_registered_images', 0)}`",
        f"- Sparse 3D points: `{result.get('best_num_points3D', 0)}`",
        f"- Sparse PLY vertices: `{result.get('sparse_ply_vertex_count', 0)}`",
        f"- Preview PNG: `{result.get('sparse_point_cloud_preview', '')}`",
        f"- Mean reprojection error px: `{result.get('best_mean_reprojection_error_px', 0):.4f}`",
        f"- Output PLY: `{result.get('sparse_point_cloud', '')}`",
        "",
        "## Timings",
        "",
    ]
    for name, seconds in result.get("timings", {}).items():
        lines.append(f"- {name}: `{seconds}` sec")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            *[f"- {item}" for item in result.get("limitations", [])],
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a real sparse photo-to-3D reconstruction with PyCOLMAP.")
    parser.add_argument("--dataset", default="strecha_fountain", choices=sorted(DATASETS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--max-image-size", type=int, default=1200)
    parser.add_argument("--max-num-features", type=int, default=4096)
    parser.add_argument("--min-model-size", type=int, default=8)
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    dataset = DATASETS[args.dataset]
    output_dir = Path(args.output_dir).resolve()
    if args.clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset_verification = _ensure_dataset(dataset, output_dir)
    result = run_pycolmap_reconstruction(
        image_dir=Path(dataset_verification["image_dir"]),
        output_dir=output_dir / "reconstruction",
        work_dir=Path(tempfile.gettempdir()) / "a1_photo_to_3d_real" / args.dataset,
        max_image_size=args.max_image_size,
        max_num_features=args.max_num_features,
        min_model_size=args.min_model_size,
    )
    report = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "dataset": dataset,
        "dataset_verification": dataset_verification,
        "parameters": {
            "max_image_size": args.max_image_size,
            "max_num_features": args.max_num_features,
            "min_model_size": args.min_model_size,
        },
        "result": result,
        "conclusion": {
            "real_sparse_reconstruction_completed": bool(result.get("ok")),
            "dense_mesh_completed": False,
            "safe_for_measurement_or_release": False,
        },
    }
    _write_report(report, output_dir)
    print(json.dumps({"status": result["status"], "ok": result.get("ok", False), "output_dir": str(output_dir)}, ensure_ascii=False))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
