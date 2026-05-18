from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
PLANNED_BACKENDS = [
    "COLMAP SfM/MVS",
    "Meshroom/AliceVision",
    "Nerfstudio Splatfacto",
]


def _quote(path: Path) -> str:
    return f'"{path}"'


def discover_images(input_dir: Path) -> list[Path]:
    if not input_dir.exists() or not input_dir.is_dir():
        return []
    return sorted(path for path in input_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)


def detect_dependencies() -> dict[str, bool]:
    return {
        "colmap": shutil.which("colmap") is not None,
        "meshroom_batch": shutil.which("meshroom_batch") is not None,
        "ns-process-data": shutil.which("ns-process-data") is not None,
        "ns-train": shutil.which("ns-train") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
    }


def _colmap_commands(input_dir: Path, output_dir: Path) -> list[str]:
    database_path = output_dir / "colmap" / "database.db"
    sparse_dir = output_dir / "colmap" / "sparse"
    dense_dir = output_dir / "colmap" / "dense"
    return [
        f"colmap feature_extractor --database_path {_quote(database_path)} --image_path {_quote(input_dir)}",
        f"colmap exhaustive_matcher --database_path {_quote(database_path)}",
        f"colmap mapper --database_path {_quote(database_path)} --image_path {_quote(input_dir)} --output_path {_quote(sparse_dir)}",
        f"colmap image_undistorter --image_path {_quote(input_dir)} --input_path {_quote(sparse_dir / '0')} --output_path {_quote(dense_dir)} --output_type COLMAP",
        f"colmap patch_match_stereo --workspace_path {_quote(dense_dir)} --workspace_format COLMAP --PatchMatchStereo.geom_consistency true",
        f"colmap stereo_fusion --workspace_path {_quote(dense_dir)} --workspace_format COLMAP --input_type geometric --output_path {_quote(dense_dir / 'fused.ply')}",
        f"colmap poisson_mesher --input_path {_quote(dense_dir / 'fused.ply')} --output_path {_quote(dense_dir / 'mesh.ply')}",
    ]


def _meshroom_commands(input_dir: Path, output_dir: Path) -> list[str]:
    return [
        f"meshroom_batch --input {_quote(input_dir)} --output {_quote(output_dir / 'meshroom')}",
    ]


def _nerfstudio_commands(input_dir: Path, output_dir: Path) -> list[str]:
    data_dir = output_dir / "nerfstudio-data"
    return [
        f"ns-process-data images --data {_quote(input_dir)} --output-dir {_quote(data_dir)}",
        f"ns-train splatfacto --data {_quote(data_dir)} --output-dir {_quote(output_dir / 'nerfstudio-runs')}",
    ]


def build_plan(
    *,
    job_id: str,
    input_dir: Path,
    output_dir: Path,
    backend: str,
    execute: bool = False,
) -> dict[str, Any]:
    images = discover_images(input_dir)
    dependencies = detect_dependencies()
    command_groups = {
        "colmap": _colmap_commands(input_dir, output_dir),
        "meshroom": _meshroom_commands(input_dir, output_dir),
        "nerfstudio": _nerfstudio_commands(input_dir, output_dir),
    }
    selected_commands: list[str]
    if backend == "dry-run":
        selected_commands = []
    else:
        selected_commands = command_groups[backend]

    quality_passed = len(images) >= 12
    missing_dependencies: list[str] = []
    if backend == "colmap" and not dependencies["colmap"]:
        missing_dependencies.append("colmap")
    if backend == "meshroom" and not dependencies["meshroom_batch"]:
        missing_dependencies.append("meshroom_batch")
    if backend == "nerfstudio":
        for name in ("ns-process-data", "ns-train"):
            if not dependencies[name]:
                missing_dependencies.append(name)

    status = "planned"
    if not quality_passed:
        status = "blocked_quality_gate"
    elif execute and missing_dependencies:
        status = "blocked_missing_dependencies"
    elif execute and backend != "dry-run":
        status = "ready_to_execute"

    warnings = []
    if not quality_passed:
        warnings.append("建议至少提供 12 张同一设备、不同角度、重叠充分的照片。")
    if missing_dependencies:
        warnings.append(f"当前环境缺少依赖：{', '.join(missing_dependencies)}。")
    if backend == "dry-run":
        warnings.append("dry-run 只生成任务包，不执行真实 3D 重建。")

    return {
        "job_id": job_id,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "backend": backend,
        "status": status,
        "mode": "execute" if execute else "dry_run",
        "true_3d_generation": False,
        "generation_status": "not_started",
        "input": {
            "input_dir": str(input_dir),
            "image_count": len(images),
            "images": [path.name for path in images],
            "accepted_suffixes": sorted(IMAGE_SUFFIXES),
        },
        "quality_gate": {
            "passed": quality_passed,
            "recommended_min_photo_count": 12,
            "checks": [
                "same_equipment",
                "multi_angle_overlap",
                "sharpness",
                "stable_lighting",
                "no_duplicate_views",
            ],
        },
        "dependencies": dependencies,
        "missing_dependencies": missing_dependencies,
        "planned_backends": PLANNED_BACKENDS,
        "commands": {
            "selected": selected_commands,
            "colmap": command_groups["colmap"],
            "meshroom": command_groups["meshroom"],
            "nerfstudio": command_groups["nerfstudio"],
        },
        "expected_outputs": {
            "colmap_point_cloud": str(output_dir / "colmap" / "dense" / "fused.ply"),
            "colmap_mesh": str(output_dir / "colmap" / "dense" / "mesh.ply"),
            "meshroom_output": str(output_dir / "meshroom"),
            "nerfstudio_run": str(output_dir / "nerfstudio-runs"),
            "sidecar_annotation": str(output_dir / "component_sidecar.template.json"),
        },
        "acceptance_criteria": [
            "输出文件可打开且不是空模型。",
            "关键部件可被人工标注到 component_key。",
            "存在执行日志、依赖版本和输入照片清单。",
            "通过人工质量验收前不得用于尺寸测量或安全放行。",
        ],
        "warnings": warnings,
        "limitations": [
            "Web 端当前不执行重型 3D 重建。",
            "单图 3D 存在尺度和遮挡不确定性。",
            "多图重建需要离线工具链和人工质量验收。",
            "未经过计量校准的结果不能作为检修尺寸依据。",
        ],
    }


def write_package(plan: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "photo_to_3d_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    selected_commands = plan["commands"]["selected"] or [
        "# dry-run: choose --backend colmap, meshroom, or nerfstudio to generate executable commands"
    ]
    (output_dir / "run_commands.ps1").write_text("\n".join(selected_commands) + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text(
        "\n".join(
            [
                "# Photo-to-3D Offline Package",
                "",
                f"- Job: `{plan['job_id']}`",
                f"- Backend: `{plan['backend']}`",
                f"- Status: `{plan['status']}`",
                f"- Images: `{plan['input']['image_count']}`",
                "",
                "This package records the commands and checks for offline reconstruction.",
                "The generated 3D result must be manually verified before it is used in the maintenance demo.",
                "",
                "## Limitations",
                "",
                *[f"- {item}" for item in plan["limitations"]],
            ]
        ),
        encoding="utf-8",
    )


def execute_commands(commands: list[str]) -> int:
    for command in commands:
        result = subprocess.run(command, shell=True)
        if result.returncode != 0:
            return result.returncode
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build or execute an offline photo-to-3D reconstruction package.")
    parser.add_argument("--job-id", default="manual", help="Reconstruction job id from the web system.")
    parser.add_argument("--input-dir", required=True, help="Directory containing uploaded photos.")
    parser.add_argument("--output-dir", default="", help="Directory for the generated task package.")
    parser.add_argument(
        "--backend",
        default="dry-run",
        choices=["dry-run", "colmap", "meshroom", "nerfstudio"],
        help="Offline reconstruction backend to prepare.",
    )
    parser.add_argument("--execute", action="store_true", help="Execute selected backend commands when dependencies exist.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else input_dir / "photo_to_3d_package"
    plan = build_plan(
        job_id=str(args.job_id),
        input_dir=input_dir,
        output_dir=output_dir,
        backend=args.backend,
        execute=args.execute,
    )
    write_package(plan, output_dir)
    print(json.dumps({"status": plan["status"], "package": str(output_dir)}, ensure_ascii=False))

    if args.execute:
        if plan["status"] != "ready_to_execute":
            return 2
        return execute_commands(plan["commands"]["selected"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
