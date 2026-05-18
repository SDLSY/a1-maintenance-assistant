from __future__ import annotations

import os
import shutil
import subprocess
import glob
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _command_version(command: str, args: list[str] | None = None) -> str:
    if not command:
        return ""
    try:
        result = subprocess.run(
            [command, *(args or ["--version"])],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
        )
    except Exception:
        return ""
    return (result.stdout or result.stderr or "").strip().splitlines()[0][:160]


def _python_module_version(module_name: str) -> tuple[bool, str]:
    try:
        module = __import__(module_name)
    except Exception as exc:
        return False, str(exc)[:160]
    return True, str(getattr(module, "__version__", "installed"))


def _first_existing(paths: list[Path]) -> str:
    for path in paths:
        if path.exists() and path.is_file():
            return str(path)
    return ""


def _glob_first(patterns: list[str]) -> str:
    for pattern in patterns:
        matches = [Path(item) for item in sorted(glob.glob(pattern))]
        for match in matches:
            if match.exists() and match.is_file():
                return str(match)
    return ""


def _find_tool(env_var: str, path_names: list[str], common_paths: list[Path], glob_patterns: list[str] | None = None) -> str:
    configured = os.getenv(env_var, "").strip()
    if configured and Path(configured).exists():
        return configured
    for name in path_names:
        found = shutil.which(name)
        if found:
            return found
    found_common = _first_existing(common_paths)
    if found_common:
        return found_common
    return _glob_first(glob_patterns or [])


def probe_cad_runtime() -> dict[str, Any]:
    cadquery_available, cadquery_version = _python_module_version("cadquery")
    trimesh_available, trimesh_version = _python_module_version("trimesh")
    pillow_available, pillow_version = _python_module_version("PIL")
    local_app = Path(os.getenv("LOCALAPPDATA", ""))
    program_files = Path(os.getenv("ProgramFiles", r"C:\Program Files"))
    program_files_x86 = Path(os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    freecad = _find_tool(
        "A1_FREECAD_CMD",
        ["FreeCADCmd", "freecadcmd", "freecad"],
        [
            local_app / "Programs" / "FreeCAD 1.1" / "bin" / "freecadcmd.exe",
            program_files / "FreeCAD 1.1" / "bin" / "FreeCADCmd.exe",
            program_files_x86 / "FreeCAD 1.1" / "bin" / "FreeCADCmd.exe",
        ],
        [
            str(local_app / "Programs" / "FreeCAD*" / "bin" / "freecadcmd.exe"),
            str(program_files / "FreeCAD*" / "bin" / "FreeCADCmd.exe"),
        ],
    )
    openscad = _find_tool(
        "A1_OPENSCAD",
        ["openscad"],
        [
            PROJECT_ROOT / "tools" / "openscad" / "openscad-2021.01" / "openscad.exe",
            program_files / "OpenSCAD" / "openscad.exe",
            program_files_x86 / "OpenSCAD" / "openscad.exe",
        ],
        [
            str(PROJECT_ROOT / "tools" / "openscad" / "*" / "openscad.exe"),
            str(program_files / "OpenSCAD*" / "openscad.exe"),
        ],
    )
    blender = _find_tool(
        "A1_BLENDER",
        ["blender"],
        [
            program_files / "Blender Foundation" / "Blender 4.5" / "blender.exe",
            program_files / "Blender Foundation" / "Blender 5.1" / "blender.exe",
        ],
        [str(program_files / "Blender Foundation" / "Blender*" / "blender.exe")],
    )

    tools = {
        "cadquery": {
            "available": cadquery_available,
            "command": "python -c import cadquery",
            "version": cadquery_version,
            "role": "generate STEP/STL from parametric CAD",
            "required_for_final": True,
        },
        "trimesh": {
            "available": trimesh_available,
            "command": "python -c import trimesh",
            "version": trimesh_version,
            "role": "generate browser-loadable GLB fallback",
            "required_for_final": True,
        },
        "pillow": {
            "available": pillow_available,
            "command": "python -c import PIL",
            "version": pillow_version,
            "role": "generate deterministic multi-view PNG previews",
            "required_for_final": True,
        },
        "freecad": {
            "available": bool(freecad),
            "command": freecad,
            "version": _command_version(freecad),
            "role": "validate and convert CAD artifacts",
            "required_for_final": True,
        },
        "openscad": {
            "available": bool(openscad),
            "command": openscad,
            "version": _command_version(openscad),
            "role": "validate OpenSCAD source and export fallback STL",
            "required_for_final": True,
        },
        "blender": {
            "available": bool(blender),
            "command": blender,
            "version": _command_version(blender),
            "role": "professional multi-view GLB rendering",
            "required_for_final": True,
        },
    }
    if cadquery_available and trimesh_available and pillow_available and bool(freecad) and bool(openscad) and bool(blender):
        mode = "real_render"
    elif cadquery_available and trimesh_available and pillow_available:
        mode = "python_render"
    elif cadquery_available or trimesh_available:
        mode = "partial_render"
    else:
        mode = "code_only"
    return {
        "schema_version": "cad-runtime-v1",
        "tools": tools,
        "final_pipeline_ready": mode in {"real_render", "python_render"},
        "recommended_mode": mode,
    }
