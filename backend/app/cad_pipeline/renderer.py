from __future__ import annotations

import json
import math
import subprocess
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .codegen import openscad_code
from .contracts import build_empty_artifact_manifest, file_item
from .runtime import probe_cad_runtime


def render_candidate_artifacts(artifact_dir: Path, *, spec: dict[str, Any], project_root: Path) -> dict[str, Any]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    runtime_report = probe_cad_runtime()
    manifest = build_empty_artifact_manifest()
    generation_log: list[dict[str, Any]] = []

    step_path = artifact_dir / "candidate.step"
    stl_path = artifact_dir / "candidate.stl"
    openscad_stl_path = artifact_dir / "candidate_openscad.stl"
    glb_path = artifact_dir / "candidate.glb"
    fcstd_path = artifact_dir / "candidate.FCStd"

    cadquery_result = _try_cadquery_export(spec, step_path=step_path, stl_path=stl_path)
    generation_log.append({"stage": "cadquery_export", **cadquery_result})
    if not step_path.exists():
        step_path.write_text(_fallback_step_text(spec), encoding="utf-8")
    if not stl_path.exists():
        stl_path.write_text(_fallback_stl_text(spec), encoding="utf-8")
    if not fcstd_path.exists():
        fcstd_path.write_text("Candidate FCStd placeholder. Validate in FreeCAD before standard promotion.\n", encoding="utf-8")

    glb_result = _try_trimesh_glb(spec, glb_path)
    generation_log.append({"stage": "glb_export", **glb_result})
    if not glb_path.exists():
        glb_path.write_bytes(b"glTF" + b"\x02\x00\x00\x00" + b"\x0c\x00\x00\x00")

    freecad_result = _try_freecad_validate(runtime_report, artifact_dir=artifact_dir, step_path=step_path)
    openscad_result = _try_openscad_export(runtime_report, artifact_dir=artifact_dir, spec=spec, target=openscad_stl_path)
    generation_log.extend(
        [
            {"stage": "freecad_step_validation", **freecad_result},
            {"stage": "openscad_export", **openscad_result},
        ]
    )

    render_results = {}
    for view in ["front", "side", "top", "iso"]:
        target = artifact_dir / f"render_{view}.png"
        _render_png(spec, target, view=view)
        render_results[view] = file_item(target, project_root=project_root)
    blender_result = _try_blender_render(runtime_report, artifact_dir=artifact_dir, glb_path=glb_path)
    generation_log.append({"stage": "blender_multi_view_render", **blender_result})
    if blender_result.get("ok"):
        for view in ["front", "side", "top", "iso"]:
            target = artifact_dir / f"render_{view}.png"
            render_results[view] = file_item(target, project_root=project_root)

    manifest["cad_files"]["step"] = file_item(step_path, project_root=project_root)
    manifest["cad_files"]["stl"] = file_item(stl_path, project_root=project_root)
    manifest["cad_files"]["openscad_stl"] = file_item(openscad_stl_path, project_root=project_root)
    manifest["cad_files"]["glb"] = file_item(glb_path, project_root=project_root)
    manifest["cad_files"]["fcstd"] = file_item(fcstd_path, project_root=project_root)
    manifest["renders"].update(render_results)
    manifest["quality_reports"]["freecad_validation"] = file_item(artifact_dir / "freecad_validation.json", project_root=project_root)
    manifest["quality_reports"]["blender_render"] = file_item(artifact_dir / "blender_render_report.json", project_root=project_root)
    manifest["quality_reports"]["openscad_export"] = file_item(artifact_dir / "openscad_export_report.json", project_root=project_root)
    manifest["render_engine"] = "blender" if blender_result.get("ok") else "pillow_fallback"
    manifest["generation_log"] = generation_log
    real_stages_ok = all(item.get("ok") for item in [freecad_result, openscad_result, blender_result])
    runtime_report["artifact_mode"] = "real_render" if real_stages_ok else (
        "python_render" if glb_path.exists() and any(item.get("ok") for item in generation_log) else runtime_report["recommended_mode"]
    )
    return {"runtime_report": runtime_report, "artifact_manifest": manifest}


def _tool_command(runtime_report: dict[str, Any], name: str) -> str:
    tool = (runtime_report.get("tools") or {}).get(name) or {}
    return str(tool.get("command") or "")


def _run_tool(command: list[str], *, timeout: int) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:800], "command": command}
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": (result.stdout or "")[-1200:],
        "stderr": (result.stderr or "")[-1200:],
        "command": command,
    }


def _cli_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def _try_freecad_validate(runtime_report: dict[str, Any], *, artifact_dir: Path, step_path: Path) -> dict[str, Any]:
    freecad = _tool_command(runtime_report, "freecad")
    report_path = artifact_dir / "freecad_validation.json"
    script_path = artifact_dir / "freecad_validate.py"
    if not freecad:
        report = {"ok": False, "available": False, "error": "FreeCADCmd not available"}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    script_path.write_text(
        textwrap.dedent(
            """
            import json
            import sys

            step_path = sys.argv[-2]
            report_path = sys.argv[-1]
            report = {"ok": False, "available": True, "step_path": step_path}
            try:
                import FreeCAD
                import Import

                doc = FreeCAD.newDocument("candidate_validation")
                Import.insert(step_path, doc.Name)
                doc.recompute()
                objects = []
                for obj in doc.Objects:
                    shape = getattr(obj, "Shape", None)
                    objects.append({
                        "name": getattr(obj, "Name", ""),
                        "label": getattr(obj, "Label", ""),
                        "has_shape": bool(shape),
                        "volume": float(getattr(shape, "Volume", 0.0) or 0.0) if shape else 0.0,
                        "area": float(getattr(shape, "Area", 0.0) or 0.0) if shape else 0.0,
                    })
                report.update({
                    "ok": len(objects) > 0,
                    "object_count": len(objects),
                    "objects": objects[:20],
                    "freecad_version": ".".join(str(item) for item in FreeCAD.Version()[:3]),
                })
            except Exception as exc:
                report["error"] = str(exc)
            with open(report_path, "w", encoding="utf-8") as handle:
                json.dump(report, handle, ensure_ascii=False, indent=2)
            """
        ).strip(),
        encoding="utf-8",
    )
    result = _run_tool([freecad, _cli_path(script_path), _cli_path(step_path), _cli_path(report_path)], timeout=60)
    report = {"ok": False}
    if report_path.exists():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            report = {"ok": False, "error": "invalid FreeCAD validation JSON"}
    report.update({"command_ok": result.get("ok"), "report_path": str(report_path)})
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _try_openscad_export(
    runtime_report: dict[str, Any],
    *,
    artifact_dir: Path,
    spec: dict[str, Any],
    target: Path,
) -> dict[str, Any]:
    openscad = _tool_command(runtime_report, "openscad")
    report_path = artifact_dir / "openscad_export_report.json"
    scad_path = artifact_dir / "openscad_runtime.scad"
    if not openscad:
        report = {"ok": False, "available": False, "error": "OpenSCAD not available"}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    scad_path.write_text(openscad_code(spec), encoding="utf-8")
    result = _run_tool([openscad, "-o", str(target), str(scad_path)], timeout=80)
    report = {
        "ok": bool(result.get("ok")) and target.exists() and target.stat().st_size > 0,
        "available": True,
        "source": str(scad_path),
        "target": str(target),
        "target_bytes": target.stat().st_size if target.exists() else 0,
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "returncode": result.get("returncode"),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _try_blender_render(runtime_report: dict[str, Any], *, artifact_dir: Path, glb_path: Path) -> dict[str, Any]:
    blender = _tool_command(runtime_report, "blender")
    report_path = artifact_dir / "blender_render_report.json"
    script_path = artifact_dir / "blender_render.py"
    if not blender:
        report = {"ok": False, "available": False, "error": "Blender not available"}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    script_path.write_text(_blender_script(), encoding="utf-8")
    result = _run_tool([blender, "--background", "--python", str(script_path), "--", str(glb_path), str(artifact_dir)], timeout=120)
    renders = {view: artifact_dir / f"render_{view}.png" for view in ["front", "side", "top", "iso"]}
    ok = bool(result.get("ok")) and all(path.exists() and path.stat().st_size > 0 for path in renders.values())
    report = {
        "ok": ok,
        "available": True,
        "engine": "blender",
        "glb_path": str(glb_path),
        "renders": {view: str(path) for view, path in renders.items()},
        "render_bytes": {view: path.stat().st_size if path.exists() else 0 for view, path in renders.items()},
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "returncode": result.get("returncode"),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _blender_script() -> str:
    return r'''
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
glb_path = Path(args[0])
out_dir = Path(args[1])

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath=str(glb_path))

mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
palette = {
    "pump_casing": (0.22, 0.50, 0.60, 1.0),
    "pump_front_cover": (0.48, 0.68, 0.74, 1.0),
    "pump_inlet": (0.66, 0.78, 0.82, 1.0),
    "pump_outlet": (0.66, 0.78, 0.82, 1.0),
    "mechanical_seal": (0.95, 0.55, 0.18, 1.0),
    "pump_shaft": (0.20, 0.24, 0.30, 1.0),
    "pump_base": (0.34, 0.42, 0.48, 1.0),
    "motor": (0.30, 0.45, 0.63, 1.0),
    "bearing": (0.20, 0.58, 0.52, 1.0),
    "engine": (0.58, 0.50, 0.40, 1.0),
}
for obj in mesh_objects:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    try:
        bpy.ops.object.shade_smooth()
    except Exception:
        pass
    obj.select_set(False)
    name = obj.name.lower()
    color = (0.42, 0.58, 0.66, 1.0)
    for key, value in palette.items():
        if key in name:
            color = value
            break
    mat = bpy.data.materials.new(name=f"{obj.name}_mat")
    mat.diffuse_color = color
    obj.data.materials.clear()
    obj.data.materials.append(mat)

if not mesh_objects:
    raise RuntimeError("No mesh objects imported from GLB")

min_corner = Vector((min((obj.matrix_world @ Vector(corner)).x for obj in mesh_objects for corner in obj.bound_box),
                     min((obj.matrix_world @ Vector(corner)).y for obj in mesh_objects for corner in obj.bound_box),
                     min((obj.matrix_world @ Vector(corner)).z for obj in mesh_objects for corner in obj.bound_box)))
max_corner = Vector((max((obj.matrix_world @ Vector(corner)).x for obj in mesh_objects for corner in obj.bound_box),
                     max((obj.matrix_world @ Vector(corner)).y for obj in mesh_objects for corner in obj.bound_box),
                     max((obj.matrix_world @ Vector(corner)).z for obj in mesh_objects for corner in obj.bound_box)))
center = (min_corner + max_corner) * 0.5
radius = max((max_corner - min_corner).length * 0.72, 2.0)

bpy.context.scene.render.engine = "BLENDER_WORKBENCH"
try:
    bpy.context.scene.display.shading.light = "STUDIO"
    bpy.context.scene.display.shading.color_type = "MATERIAL"
    bpy.context.scene.display.shading.background_type = "VIEWPORT"
    bpy.context.scene.display.shading.background_color = (0.96, 0.98, 0.98)
except Exception:
    pass
bpy.context.scene.render.resolution_x = 960
bpy.context.scene.render.resolution_y = 640
bpy.context.scene.render.film_transparent = False
bpy.context.scene.view_settings.view_transform = "Standard"
bpy.context.scene.view_settings.look = "Medium High Contrast"
bpy.context.scene.view_settings.exposure = 0.0
bpy.context.scene.view_settings.gamma = 1.0
bpy.context.scene.world = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world.color = (1.0, 1.0, 1.0)

light_data = bpy.data.lights.new("key_area", type="AREA")
light_data.energy = 950
light_data.size = radius * 3.0
light = bpy.data.objects.new("key_area", light_data)
bpy.context.collection.objects.link(light)
light.location = center + Vector((radius * 1.8, -radius * 2.2, radius * 2.0))

fill_data = bpy.data.lights.new("fill_area", type="AREA")
fill_data.energy = 220
fill_data.size = radius * 4.0
fill = bpy.data.objects.new("fill_area", fill_data)
bpy.context.collection.objects.link(fill)
fill.location = center + Vector((-radius * 2.0, radius * 1.6, radius * 1.3))

camera_data = bpy.data.cameras.new("Camera")
camera = bpy.data.objects.new("Camera", camera_data)
bpy.context.collection.objects.link(camera)
bpy.context.scene.camera = camera
camera.data.lens = 58
camera.data.type = "ORTHO"
camera.data.ortho_scale = radius * 2.35

def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

views = {
    "front": Vector((center.x, center.y - radius * 2.7, center.z + radius * 0.35)),
    "side": Vector((center.x + radius * 2.7, center.y, center.z + radius * 0.35)),
    "top": Vector((center.x, center.y - radius * 0.08, center.z + radius * 3.1)),
    "iso": Vector((center.x + radius * 2.0, center.y - radius * 2.0, center.z + radius * 1.35)),
}

for name, location in views.items():
    camera.location = location
    look_at(camera, center)
    bpy.context.scene.render.filepath = str(out_dir / f"render_{name}.png")
    bpy.ops.render.render(write_still=True)
'''.strip()


def _try_cadquery_export(spec: dict[str, Any], *, step_path: Path, stl_path: Path) -> dict[str, Any]:
    try:
        import cadquery as cq
        from cadquery import exporters

        model = _cadquery_model(cq, spec)
        exporters.export(model, str(step_path))
        exporters.export(model, str(stl_path))
        return {"ok": True, "step": str(step_path), "stl": str(stl_path)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:500]}


def _cadquery_model(cq: Any, spec: dict[str, Any]) -> Any:
    equipment = spec.get("equipment", "general")
    p = spec.get("parameters", {})
    if equipment == "bearing":
        outer_diameter = float(p.get("outer_diameter", 52))
        inner_diameter = float(p.get("inner_diameter", 25))
        width = float(p.get("width", 15))
        return cq.Workplane("XY").circle(outer_diameter / 2).circle(inner_diameter / 2).extrude(width)
    if equipment == "pump":
        body_length = float(p.get("body_length", 150))
        body_height = float(p.get("body_height", 96))
        port_diameter = float(p.get("port_diameter", 48))
        casing = cq.Workplane("YZ").circle(body_height * 0.46).extrude(58).translate((-29, 0, 0))
        front_cover = cq.Workplane("YZ").circle(body_height * 0.34).extrude(12).translate((-47, 0, 0))
        inlet = cq.Workplane("YZ").circle(port_diameter / 2).extrude(92).translate((-132, 0, 0))
        inlet_flange = cq.Workplane("YZ").circle(port_diameter * 0.66).extrude(12).translate((-138, 0, 0))
        outlet = cq.Workplane("XY").circle(port_diameter * 0.41).extrude(82).translate((0, 0, body_height * 0.31))
        outlet_flange = cq.Workplane("XY").circle(port_diameter * 0.55).extrude(12).translate((0, 0, body_height * 0.31 + 76))
        seal = cq.Workplane("YZ").circle(27).circle(11).extrude(24).translate((44, 0, 0))
        shaft = cq.Workplane("YZ").circle(float(p.get("shaft_diameter", 18)) / 2).extrude(138).translate((68, 0, 0))
        base = cq.Workplane("XY").box(126, 86, 12).translate((12, 0, -body_height * 0.56))
        foot_a = cq.Workplane("XY").box(32, 22, 18).translate((-36, -32, -body_height * 0.42))
        foot_b = cq.Workplane("XY").box(32, 22, 18).translate((60, 32, -body_height * 0.42))
        return (
            casing.union(front_cover)
            .union(inlet)
            .union(inlet_flange)
            .union(outlet)
            .union(outlet_flange)
            .union(seal)
            .union(shaft)
            .union(base)
            .union(foot_a)
            .union(foot_b)
        )
    if equipment == "motor":
        body_length = float(p.get("body_length", 180))
        body_diameter = float(p.get("body_diameter", 92))
        shaft_diameter = float(p.get("shaft_diameter", 18))
        body = cq.Workplane("YZ").circle(body_diameter / 2).extrude(body_length)
        shaft = cq.Workplane("YZ").circle(shaft_diameter / 2).extrude(body_length * 1.25)
        terminal = cq.Workplane("XY").box(42, 32, 28).translate((body_length * 0.16, 0, body_diameter / 2 + 14))
        return body.union(shaft).union(terminal)
    block_width = float(p.get("block_width", 120))
    block_height = float(p.get("block_height", 130))
    block = cq.Workplane("XY").box(block_width, 70, block_height).edges("|Z").fillet(4)
    plug = cq.Workplane("XY").circle(7).extrude(36).translate((0, 0, block_height / 2))
    return block.union(plug)


def _try_trimesh_glb(spec: dict[str, Any], target: Path) -> dict[str, Any]:
    try:
        import numpy as np
        import trimesh

        scene = trimesh.Scene()
        equipment = spec.get("equipment", "general")
        p = spec.get("parameters", {})
        if equipment == "bearing":
            outer = trimesh.creation.cylinder(radius=float(p.get("outer_diameter", 52)) / 2, height=float(p.get("width", 15)), sections=96)
            inner = trimesh.creation.cylinder(radius=float(p.get("inner_diameter", 25)) / 2, height=float(p.get("width", 15)) * 1.08, sections=64)
            outer.visual.vertex_colors = [36, 108, 100, 210]
            inner.visual.vertex_colors = [240, 250, 248, 210]
            scene.add_geometry(outer, node_name="outer_ring_candidate")
            scene.add_geometry(inner, node_name="inner_bore_reference")
        elif equipment == "pump":
            body_height = float(p.get("body_height", 96))
            port_radius = float(p.get("port_diameter", 48)) / 2
            casing = trimesh.creation.cylinder(radius=body_height * 0.46, height=58, sections=96)
            casing_cover = trimesh.creation.cylinder(radius=body_height * 0.34, height=14, sections=96)
            inlet = trimesh.creation.cylinder(radius=port_radius, height=92, sections=72)
            inlet_flange = trimesh.creation.cylinder(radius=port_radius * 1.32, height=12, sections=72)
            outlet = trimesh.creation.cylinder(radius=port_radius * 0.82, height=82, sections=72)
            outlet_flange = trimesh.creation.cylinder(radius=port_radius * 1.10, height=12, sections=72)
            seal = trimesh.creation.cylinder(radius=27, height=24, sections=72)
            shaft = trimesh.creation.cylinder(radius=float(p.get("shaft_diameter", 18)) / 2, height=138, sections=48)
            base = trimesh.creation.box(extents=[126, 86, 12])
            foot_a = trimesh.creation.box(extents=[32, 22, 18])
            foot_b = trimesh.creation.box(extents=[32, 22, 18])
            for mesh, color in [
                (casing, [62, 129, 153, 255]),
                (casing_cover, [116, 169, 184, 255]),
                (inlet, [170, 201, 211, 255]),
                (inlet_flange, [129, 171, 185, 255]),
                (outlet, [170, 201, 211, 255]),
                (outlet_flange, [129, 171, 185, 255]),
                (seal, [229, 154, 59, 255]),
                (shaft, [63, 73, 88, 255]),
                (base, [81, 104, 121, 255]),
                (foot_a, [81, 104, 121, 255]),
                (foot_b, [81, 104, 121, 255]),
            ]:
                mesh.visual.vertex_colors = color
            scene.add_geometry(casing, node_name="pump_casing_candidate", transform=_rotation_y(np, math.pi / 2))
            scene.add_geometry(casing_cover, node_name="pump_front_cover_candidate", transform=_translation(np, [-36, 0, 0]) @ _rotation_y(np, math.pi / 2))
            scene.add_geometry(inlet, node_name="pump_inlet_candidate", transform=_translation(np, [-78, 0, 0]) @ _rotation_y(np, math.pi / 2))
            scene.add_geometry(inlet_flange, node_name="pump_inlet_flange_candidate", transform=_translation(np, [-124, 0, 0]) @ _rotation_y(np, math.pi / 2))
            scene.add_geometry(outlet, node_name="pump_outlet_candidate", transform=_translation(np, [0, 0, 68]))
            scene.add_geometry(outlet_flange, node_name="pump_outlet_flange_candidate", transform=_translation(np, [0, 0, 112]))
            scene.add_geometry(seal, node_name="mechanical_seal_candidate", transform=_translation(np, [48, 0, 0]) @ _rotation_y(np, math.pi / 2))
            scene.add_geometry(shaft, node_name="pump_shaft_candidate", transform=_translation(np, [86, 0, 0]) @ _rotation_y(np, math.pi / 2))
            scene.add_geometry(base, node_name="pump_base_candidate", transform=_translation(np, [12, 0, -54]))
            scene.add_geometry(foot_a, node_name="pump_left_foot_candidate", transform=_translation(np, [-36, -32, -40]))
            scene.add_geometry(foot_b, node_name="pump_right_foot_candidate", transform=_translation(np, [60, 32, -40]))
        elif equipment == "motor":
            body = trimesh.creation.cylinder(radius=float(p.get("body_diameter", 92)) / 2, height=float(p.get("body_length", 180)), sections=96)
            shaft = trimesh.creation.cylinder(radius=float(p.get("shaft_diameter", 18)) / 2, height=float(p.get("body_length", 180)) * 1.25, sections=48)
            body.visual.vertex_colors = [80, 115, 150, 220]
            shaft.visual.vertex_colors = [70, 80, 92, 240]
            scene.add_geometry(body, node_name="motor_body_candidate", transform=_rotation_y(np, math.pi / 2))
            scene.add_geometry(shaft, node_name="motor_shaft_candidate", transform=_rotation_y(np, math.pi / 2))
        else:
            block = trimesh.creation.box(extents=[float(p.get("block_width", 120)), 72, float(p.get("block_height", 130))])
            plug = trimesh.creation.cylinder(radius=7, height=42, sections=32)
            block.visual.vertex_colors = [145, 124, 100, 220]
            plug.visual.vertex_colors = [235, 225, 205, 240]
            scene.add_geometry(block, node_name="engine_block_candidate")
            scene.add_geometry(plug, node_name="spark_plug_candidate", transform=_translation(np, [0, 0, 76]))
        target.write_bytes(scene.export(file_type="glb"))
        return {"ok": True, "path": str(target)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:500]}


def _translation(np: Any, xyz: list[float]) -> Any:
    matrix = np.eye(4)
    matrix[:3, 3] = xyz
    return matrix


def _rotation_y(np: Any, radians: float) -> Any:
    c = math.cos(radians)
    s = math.sin(radians)
    matrix = np.eye(4)
    matrix[0, 0] = c
    matrix[0, 2] = s
    matrix[2, 0] = -s
    matrix[2, 2] = c
    return matrix


def _render_png(spec: dict[str, Any], target: Path, *, view: str) -> None:
    image = Image.new("RGB", (960, 640), "#f5f8f7")
    draw = ImageDraw.Draw(image)
    title = f"{spec.get('equipment', 'candidate').upper()} candidate CAD - {view}"
    draw.rectangle([0, 0, 960, 72], fill="#102233")
    draw.text((32, 24), title, fill="#ffffff")
    draw.text((32, 600), "Candidate CAD: not for measurement, manufacturing, or safety release.", fill="#64748b")
    equipment = spec.get("equipment", "")
    if equipment == "pump":
        _draw_pump(draw, view)
    elif equipment == "motor":
        _draw_motor(draw, view)
    elif equipment == "engine":
        _draw_engine(draw, view)
    else:
        _draw_bearing(draw, view)
    image.save(target)


def _draw_pump(draw: ImageDraw.ImageDraw, view: str) -> None:
    offset = 30 if view == "iso" else 0
    draw.rounded_rectangle([230 + offset, 205, 620 + offset, 425], radius=58, fill="#b9d9d4", outline="#1d6f65", width=7)
    draw.ellipse([240 + offset, 245, 410 + offset, 415], fill="#f7fbfb", outline="#1d6f65", width=7)
    draw.rounded_rectangle([600 + offset, 278, 770 + offset, 356], radius=18, fill="#dfeceb", outline="#1d6f65", width=5)
    draw.rounded_rectangle([414 + offset, 124, 520 + offset, 226], radius=18, fill="#dfeceb", outline="#1d6f65", width=5)
    draw.ellipse([420 + offset, 274, 500 + offset, 354], fill="#e3a33c", outline="#854d0e", width=5)
    draw.line([470 + offset, 314, 760 + offset, 314], fill="#334155", width=14)


def _draw_motor(draw: ImageDraw.ImageDraw, view: str) -> None:
    offset = 28 if view == "iso" else 0
    draw.rounded_rectangle([235 + offset, 230, 680 + offset, 410], radius=90, fill="#c7d9ea", outline="#355c7d", width=7)
    draw.ellipse([216 + offset, 225, 398 + offset, 415], outline="#355c7d", width=7)
    draw.ellipse([520 + offset, 225, 704 + offset, 415], outline="#355c7d", width=7)
    draw.line([150 + offset, 320, 790 + offset, 320], fill="#26384a", width=18)
    draw.rounded_rectangle([390 + offset, 135, 525 + offset, 222], radius=14, fill="#eef5f8", outline="#355c7d", width=5)


def _draw_bearing(draw: ImageDraw.ImageDraw, view: str) -> None:
    offset = 24 if view == "iso" else 0
    draw.ellipse([310 + offset, 150, 650 + offset, 490], fill="#d9ebe8", outline="#1d6f65", width=8)
    draw.ellipse([400 + offset, 240, 560 + offset, 400], fill="#f8fbfa", outline="#1d6f65", width=7)
    cx, cy = 480 + offset, 320
    for i in range(8):
        angle = i * math.pi / 4
        x = cx + math.cos(angle) * 118
        y = cy + math.sin(angle) * 118
        draw.ellipse([x - 17, y - 17, x + 17, y + 17], fill="#e3a33c", outline="#854d0e", width=4)


def _draw_engine(draw: ImageDraw.ImageDraw, view: str) -> None:
    offset = 26 if view == "iso" else 0
    draw.rounded_rectangle([330 + offset, 215, 625 + offset, 455], radius=18, fill="#ded3c4", outline="#6f5842", width=7)
    for y in [238, 270, 302, 334, 366]:
        draw.line([295 + offset, y, 660 + offset, y], fill="#6f5842", width=6)
    draw.rounded_rectangle([445 + offset, 130, 515 + offset, 232], radius=18, fill="#f7f3ec", outline="#6f5842", width=5)
    draw.ellipse([416 + offset, 350, 544 + offset, 478], fill="#f7f3ec", outline="#6f5842", width=7)


def _fallback_step_text(spec: dict[str, Any]) -> str:
    return f"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('Tri-MRO candidate CAD fallback'),'2;1');\nENDSEC;\nDATA;\n/* {spec.get('equipment')} candidate placeholder */\nENDSEC;\nEND-ISO-10303-21;\n"


def _fallback_stl_text(spec: dict[str, Any]) -> str:
    name = str(spec.get("equipment") or "candidate")
    return f"solid {name}\nendsolid {name}\n"
