# Candidate CAD Final Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the current SVG-based candidate CAD v1 into a real, auditable photo-to-candidate-CAD pipeline that generates CAD artifacts, renders multi-view previews, compares them against the source photo, supports manual correction/review, and promotes approved candidates into the Tri-MRO structure chain.

**Architecture:** Keep the current `/api/cad/candidates` contract, but split generation into focused modules under `backend/app/cad_pipeline/`. The final pipeline remains conservative: single photos produce candidate engineering assets, not measurement-grade CAD. Browser-facing output uses GLB/PNG previews, while STEP/FCStd/CadQuery/OpenSCAD remain the traceable engineering source.

**Tech Stack:** FastAPI, SQLite, CadQuery, optional FreeCAD CLI, optional Blender CLI for GLB/PNG rendering, Three.js frontend, Vue single-page frontend, pytest.

---

## Current State

The v1 implementation already exists:

- `backend/app/candidate_cad.py`: creates observation JSON, CAD spec, CadQuery/OpenSCAD code, SVG preview, cached comparison, review status.
- `backend/app/database.py`: contains `candidate_cad_assets`.
- `backend/app/main.py`: exposes `/api/cad/candidates`.
- `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`: resources page shows “候选 CAD 资产池”.
- `docs/CANDIDATE_CAD_ASSET_PIPELINE.md`: documents current v1.

Main gap:

- Current preview is deterministic SVG, not real CAD rendering.
- Generated CadQuery/OpenSCAD code is saved, but not executed in a sandbox.
- No STEP/STL/GLB/PNG artifact set.
- No manual CAD spec editor.
- No approved-candidate integration with CAD workbench.

## Target Final Effect

The final feature should show a professional “照片驱动的 CAD 资产审核工位”:

```text
现场照片
-> VLM/OCR 观察
-> 可编辑 CAD spec
-> CadQuery/OpenSCAD/FreeCAD 生成 STEP/STL/GLB
-> front/side/top/isometric PNG 渲染
-> VLM/规则对比报告
-> 人工修正部件树、孔位、尺寸来源、component_key
-> 审核通过进入候选资产池
-> 可在 CAD 结构工位作为候选结构链资产加载
```

It must always display this boundary:

```text
候选 CAD 非测量模型，不用于制造或安全放行。
```

---

## File Structure

Create:

- `backend/app/cad_pipeline/__init__.py`
- `backend/app/cad_pipeline/contracts.py`
  - Typed payload builders for observation, spec, artifacts, rendering, comparison, review gate.
- `backend/app/cad_pipeline/runtime.py`
  - Detects CadQuery, FreeCAD, OpenSCAD, Blender availability.
- `backend/app/cad_pipeline/spec_builder.py`
  - Converts visual asset + OCR/VLM analysis into editable CAD spec.
- `backend/app/cad_pipeline/codegen.py`
  - Generates CadQuery and OpenSCAD code from CAD spec.
- `backend/app/cad_pipeline/executor.py`
  - Runs code in a limited artifact directory with timeout and command allowlist.
- `backend/app/cad_pipeline/renderer.py`
  - Produces STEP/STL/GLB and multi-view PNG previews when runtime tools exist.
- `backend/app/cad_pipeline/comparator.py`
  - Compares source photo, spec, and renders; produces traceable score and failure reasons.
- `backend/app/cad_pipeline/promotion.py`
  - Converts approved candidate into a candidate model entry for CAD workbench.
- `scripts/verify_cad_pipeline_runtime.py`
  - CLI check for CadQuery/FreeCAD/OpenSCAD/Blender availability.
- `tests/test_candidate_cad_final_pipeline.py`
  - End-to-end backend contract and artifact tests.
- `tests/test_candidate_cad_frontend.py`
  - Static frontend checks for final workbench controls.
- `docs/CANDIDATE_CAD_FINAL_PIPELINE.md`
  - Final user-facing design and risk boundary.

Modify:

- `backend/app/candidate_cad.py`
  - Keep API-facing orchestration, move internals into `cad_pipeline`.
- `backend/app/database.py`
  - Add columns for `editable_spec_json`, `artifact_manifest_json`, `runtime_report_json`, `promotion_json`.
- `backend/app/main.py`
  - Add endpoints for spec update, render/retry, promotion, artifact manifest.
- `backend/app/schemas.py`
  - Add request models for spec patch, render retry, promotion.
- `frontend/index.html`
  - Upgrade candidate CAD section into a review workbench.
- `frontend/app.js`
  - Add spec edit/retry/promote actions and artifact manifest loading.
- `frontend/styles.css`
  - Add professional CAD workbench layout.

---

## Task 1: Runtime Probe And Contract Tests

**Files:**

- Create: `tests/test_candidate_cad_final_pipeline.py`
- Create: `backend/app/cad_pipeline/runtime.py`
- Create: `scripts/verify_cad_pipeline_runtime.py`

- [ ] **Step 1: Write failing tests for runtime probe**

Add this test:

```python
from pathlib import Path

from backend.app.cad_pipeline.runtime import probe_cad_runtime


def test_cad_runtime_probe_returns_declared_tools() -> None:
    report = probe_cad_runtime()
    assert report["schema_version"] == "cad-runtime-v1"
    assert {"cadquery", "freecad", "openscad", "blender"} <= set(report["tools"])
    for tool in report["tools"].values():
        assert {"available", "command", "version", "role", "required_for_final"} <= set(tool)
    assert report["final_pipeline_ready"] in {True, False}
    assert report["recommended_mode"] in {"real_render", "partial_render", "code_only"}
```

- [ ] **Step 2: Verify test fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_cad_runtime_probe_returns_declared_tools -q
```

Expected: FAIL because `backend.app.cad_pipeline.runtime` does not exist.

- [ ] **Step 3: Implement runtime probe**

Create `backend/app/cad_pipeline/__init__.py` as an empty module.

Create `backend/app/cad_pipeline/runtime.py`:

```python
from __future__ import annotations

import shutil
import subprocess
from typing import Any


def _version(command: str, args: list[str]) -> str:
    if not command:
        return ""
    try:
        result = subprocess.run(
            [command, *args],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception:
        return ""
    return (result.stdout or result.stderr or "").strip().splitlines()[0][:160]


def probe_cad_runtime() -> dict[str, Any]:
    cadquery_available = False
    cadquery_version = ""
    try:
        import cadquery as cq  # type: ignore

        cadquery_available = True
        cadquery_version = getattr(cq, "__version__", "installed")
    except Exception:
        cadquery_available = False

    freecad = shutil.which("FreeCADCmd") or shutil.which("freecadcmd") or ""
    openscad = shutil.which("openscad") or ""
    blender = shutil.which("blender") or ""

    tools = {
        "cadquery": {
            "available": cadquery_available,
            "command": "python -c import cadquery",
            "version": cadquery_version,
            "role": "generate STEP/STL from parametric Python CAD",
            "required_for_final": True,
        },
        "freecad": {
            "available": bool(freecad),
            "command": freecad,
            "version": _version(freecad, ["--version"]),
            "role": "validate/open/export CAD artifacts",
            "required_for_final": False,
        },
        "openscad": {
            "available": bool(openscad),
            "command": openscad,
            "version": _version(openscad, ["--version"]),
            "role": "generate STL from OpenSCAD fallback",
            "required_for_final": False,
        },
        "blender": {
            "available": bool(blender),
            "command": blender,
            "version": _version(blender, ["--version"]),
            "role": "render PNG views and convert mesh to GLB",
            "required_for_final": True,
        },
    }
    real_ready = tools["cadquery"]["available"] and tools["blender"]["available"]
    partial_ready = tools["cadquery"]["available"] or tools["openscad"]["available"] or tools["freecad"]["available"]
    return {
        "schema_version": "cad-runtime-v1",
        "tools": tools,
        "final_pipeline_ready": bool(real_ready),
        "recommended_mode": "real_render" if real_ready else "partial_render" if partial_ready else "code_only",
    }
```

Create `scripts/verify_cad_pipeline_runtime.py`:

```python
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.cad_pipeline.runtime import probe_cad_runtime


if __name__ == "__main__":
    print(json.dumps(probe_cad_runtime(), ensure_ascii=False, indent=2))
```

- [ ] **Step 4: Run test to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_cad_runtime_probe_returns_declared_tools -q
```

Expected: PASS.

---

## Task 2: Artifact Manifest Schema

**Files:**

- Modify: `backend/app/database.py`
- Create: `backend/app/cad_pipeline/contracts.py`
- Modify: `tests/test_candidate_cad_final_pipeline.py`

- [ ] **Step 1: Write failing test for artifact manifest**

Append:

```python
from backend.app.cad_pipeline.contracts import build_empty_artifact_manifest


def test_artifact_manifest_contains_real_cad_targets() -> None:
    manifest = build_empty_artifact_manifest()
    assert manifest["schema_version"] == "candidate-cad-artifacts-v1"
    assert {"step", "stl", "glb"} <= set(manifest["cad_files"])
    assert {"front", "side", "top", "iso"} <= set(manifest["renders"])
    assert manifest["quality_gates"]["human_review_required"] is True
    assert manifest["risk_boundary"]["not_for_measurement"] is True
```

- [ ] **Step 2: Verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_artifact_manifest_contains_real_cad_targets -q
```

Expected: FAIL because `contracts.py` does not exist.

- [ ] **Step 3: Implement contracts**

Create `backend/app/cad_pipeline/contracts.py`:

```python
from __future__ import annotations

from typing import Any


def risk_boundary() -> dict[str, Any]:
    return {
        "not_for_measurement": True,
        "not_for_manufacturing": True,
        "not_for_safety_release": True,
        "allowed_use": ["candidate CAD drafting", "structure-chain grounding", "manual review"],
        "required_gate": "mechanical human review before standard asset promotion",
    }


def build_empty_artifact_manifest() -> dict[str, Any]:
    return {
        "schema_version": "candidate-cad-artifacts-v1",
        "cad_files": {
            "step": {"path": "", "exists": False, "bytes": 0},
            "stl": {"path": "", "exists": False, "bytes": 0},
            "glb": {"path": "", "exists": False, "bytes": 0},
            "fcstd": {"path": "", "exists": False, "bytes": 0},
        },
        "renders": {
            "front": {"path": "", "exists": False, "bytes": 0},
            "side": {"path": "", "exists": False, "bytes": 0},
            "top": {"path": "", "exists": False, "bytes": 0},
            "iso": {"path": "", "exists": False, "bytes": 0},
        },
        "source_files": {
            "cadquery": {"path": "", "exists": False, "bytes": 0},
            "openscad": {"path": "", "exists": False, "bytes": 0},
            "cad_spec": {"path": "", "exists": False, "bytes": 0},
        },
        "quality_gates": {
            "human_review_required": True,
            "vlm_compare_required": True,
            "runtime_report_required": True,
        },
        "risk_boundary": risk_boundary(),
    }
```

Modify `backend/app/database.py` in `init_db()` after current candidate table creation:

```python
    _ensure_column(conn, "candidate_cad_assets", "editable_spec_json", "TEXT DEFAULT '{}'")
    _ensure_column(conn, "candidate_cad_assets", "artifact_manifest_json", "TEXT DEFAULT '{}'")
    _ensure_column(conn, "candidate_cad_assets", "runtime_report_json", "TEXT DEFAULT '{}'")
    _ensure_column(conn, "candidate_cad_assets", "promotion_json", "TEXT DEFAULT '{}'")
```

- [ ] **Step 4: Run test**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_artifact_manifest_contains_real_cad_targets -q
```

Expected: PASS.

---

## Task 3: Replace SVG-Only Renderer With Real Artifact Pipeline

**Files:**

- Create: `backend/app/cad_pipeline/codegen.py`
- Create: `backend/app/cad_pipeline/executor.py`
- Create: `backend/app/cad_pipeline/renderer.py`
- Modify: `backend/app/candidate_cad.py`
- Modify: `tests/test_candidate_cad_final_pipeline.py`

- [ ] **Step 1: Write failing e2e artifact test**

Append:

```python
import os
from fastapi.testclient import TestClient

from backend.app.database import reset_demo_db
from backend.app.main import app


client = TestClient(app)


def setup_module() -> None:
    os.environ["ACTIVE_MODEL_PROVIDER"] = "local"
    reset_demo_db()


def test_candidate_cad_generation_returns_real_artifact_manifest() -> None:
    image_path = Path(__file__).resolve().parents[1] / "data" / "image_eval" / "images" / "pump_mechanical_seal_parts_02.jpg"
    if not image_path.exists():
        image_path = next((Path(__file__).resolve().parents[1] / "data" / "image_eval" / "images").glob("*.jpg"))
    with image_path.open("rb") as handle:
        uploaded = client.post("/api/upload-image", files={"file": (image_path.name, handle, "image/jpeg")}).json()
    response = client.post(
        "/api/cad/candidates/from-visual",
        json={"visual_asset_id": uploaded["visual_asset_id"], "equipment": "pump", "model": "ISG80-160"},
    )
    assert response.status_code == 200
    candidate = response.json()["candidate"]
    manifest = candidate["artifact_manifest"]
    assert manifest["schema_version"] == "candidate-cad-artifacts-v1"
    assert manifest["source_files"]["cadquery"]["exists"] is True
    assert manifest["source_files"]["openscad"]["exists"] is True
    assert manifest["cad_files"]["step"]["path"].endswith(".step")
    assert manifest["cad_files"]["stl"]["path"].endswith(".stl")
    assert manifest["cad_files"]["glb"]["path"].endswith(".glb")
    assert manifest["renders"]["iso"]["path"].endswith(".png")
    assert candidate["runtime_report"]["recommended_mode"] in {"real_render", "partial_render", "code_only"}
```

- [ ] **Step 2: Verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_candidate_cad_generation_returns_real_artifact_manifest -q
```

Expected: FAIL because candidates do not return `artifact_manifest`.

- [ ] **Step 3: Implement codegen extraction**

Move existing `_cadquery_code()` and `_openscad_code()` out of `candidate_cad.py` into `backend/app/cad_pipeline/codegen.py`:

```python
from __future__ import annotations

from typing import Any


def cadquery_code(spec: dict[str, Any]) -> str:
    # paste the current _cadquery_code body here and keep output identical
    ...


def openscad_code(spec: dict[str, Any]) -> str:
    # paste the current _openscad_code body here and keep output identical
    ...
```

Remove duplicate code from `candidate_cad.py` after imports have been updated.

- [ ] **Step 4: Implement executor**

Create `backend/app/cad_pipeline/executor.py`:

```python
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def run_command(command: list[str], *, cwd: Path, timeout: int = 45) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
            "command": command,
        }
    except Exception as exc:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(exc), "command": command}
```

- [ ] **Step 5: Implement renderer with graceful degradation**

Create `backend/app/cad_pipeline/renderer.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import build_empty_artifact_manifest
from .runtime import probe_cad_runtime


def _file_item(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}


def render_candidate_artifacts(artifact_dir: Path, *, spec: dict[str, Any]) -> dict[str, Any]:
    runtime = probe_cad_runtime()
    manifest = build_empty_artifact_manifest()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    step = artifact_dir / "candidate.step"
    stl = artifact_dir / "candidate.stl"
    glb = artifact_dir / "candidate.glb"
    fcstd = artifact_dir / "candidate.FCStd"
    for path in [step, stl, glb, fcstd]:
        if not path.exists():
            path.write_text(
                f"Placeholder {path.suffix} for {spec.get('equipment')} candidate. Replace via CadQuery/FreeCAD runtime.\\n",
                encoding="utf-8",
            )
    for view in ["front", "side", "top", "iso"]:
        png = artifact_dir / f"render_{view}.png"
        if not png.exists():
            png.write_bytes(_minimal_png())

    manifest["cad_files"]["step"] = _file_item(step)
    manifest["cad_files"]["stl"] = _file_item(stl)
    manifest["cad_files"]["glb"] = _file_item(glb)
    manifest["cad_files"]["fcstd"] = _file_item(fcstd)
    for view in ["front", "side", "top", "iso"]:
        manifest["renders"][view] = _file_item(artifact_dir / f"render_{view}.png")
    return {"runtime_report": runtime, "artifact_manifest": manifest}


def _minimal_png() -> bytes:
    return (
        b"\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01"
        b"\\x08\\x06\\x00\\x00\\x00\\x1f\\x15\\xc4\\x89\\x00\\x00\\x00\\x0cIDATx\\x9cc``\\x00\\x00"
        b"\\x00\\x04\\x00\\x01\\xf6\\x178U\\x00\\x00\\x00\\x00IEND\\xaeB`\\x82"
    )
```

This step intentionally creates placeholder files when CAD runtimes are missing. Later tasks replace placeholders with real CadQuery/Blender output. The UI must label placeholder artifacts as `code_only` or `partial_render`.

- [ ] **Step 6: Wire renderer into `candidate_cad.py`**

In `create_candidate_from_visual_asset()`, after source code files are written, call:

```python
from .cad_pipeline.renderer import render_candidate_artifacts

rendered = render_candidate_artifacts(artifact_dir, spec=spec)
artifact_manifest = rendered["artifact_manifest"]
runtime_report = rendered["runtime_report"]
artifact_manifest["source_files"]["cadquery"] = _manifest_file(cadquery_path)
artifact_manifest["source_files"]["openscad"] = _manifest_file(openscad_path)
artifact_manifest["source_files"]["cad_spec"] = _manifest_file(spec_path)
```

Add helper:

```python
def _manifest_file(path: Path) -> dict[str, Any]:
    return {"path": _relative_path(path), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0}
```

Persist `artifact_manifest_json` and `runtime_report_json`.

Update `row_to_candidate()` to include:

```python
candidate["artifact_manifest"] = _json_loads(candidate.pop("artifact_manifest_json", ""), build_empty_artifact_manifest())
candidate["runtime_report"] = _json_loads(candidate.pop("runtime_report_json", ""), {})
candidate["editable_spec"] = _json_loads(candidate.pop("editable_spec_json", ""), candidate["cad_spec"])
candidate["promotion"] = _json_loads(candidate.pop("promotion_json", ""), {})
```

- [ ] **Step 7: Run e2e test**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_candidate_cad_generation_returns_real_artifact_manifest -q
```

Expected: PASS.

---

## Task 4: Spec Editing And Regeneration API

**Files:**

- Modify: `backend/app/schemas.py`
- Modify: `backend/app/candidate_cad.py`
- Modify: `backend/app/main.py`
- Modify: `tests/test_candidate_cad_final_pipeline.py`

- [ ] **Step 1: Write failing test**

Append:

```python
def test_candidate_cad_spec_can_be_patched_and_regenerated() -> None:
    listed = client.get("/api/cad/candidates").json()
    candidate_id = listed["candidates"][0]["id"]
    patch = {
        "parameters": {"body_length": 188, "port_diameter": 52},
        "review_notes": "人工修正泵体长度和法兰口径，准备重新生成候选 CAD。",
    }
    response = client.patch(f"/api/cad/candidates/{candidate_id}/spec", json=patch)
    assert response.status_code == 200
    candidate = response.json()["candidate"]
    assert candidate["editable_spec"]["parameters"]["body_length"] == 188
    assert candidate["editable_spec"]["parameters"]["port_diameter"] == 52
    assert candidate["status"] == "needs_review"
    assert "人工修正泵体长度" in candidate["review_notes"]
```

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_candidate_cad_spec_can_be_patched_and_regenerated -q
```

Expected: FAIL because PATCH endpoint is missing.

- [ ] **Step 3: Add schema**

In `backend/app/schemas.py`:

```python
class CandidateCadSpecPatchRequest(BaseModel):
    parameters: dict = Field(default_factory=dict)
    component_keys: list[str] = Field(default_factory=list)
    review_notes: str = ""
```

- [ ] **Step 4: Add patch implementation**

In `backend/app/candidate_cad.py`:

```python
def patch_candidate_spec(conn: sqlite3.Connection, candidate_id: int, *, parameters: dict, component_keys: list[str], review_notes: str) -> dict[str, Any]:
    candidate = get_candidate_asset(conn, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    editable = dict(candidate.get("editable_spec") or candidate.get("cad_spec") or {})
    editable_parameters = dict(editable.get("parameters") or {})
    editable_parameters.update(parameters or {})
    editable["parameters"] = editable_parameters
    if component_keys:
        editable["component_keys"] = component_keys
    conn.execute(
        """
        UPDATE candidate_cad_assets
        SET editable_spec_json = ?, review_notes = ?, status = 'needs_review', updated_at = ?
        WHERE id = ?
        """,
        (_json_dumps(editable), review_notes or candidate.get("review_notes", ""), _utc(), candidate_id),
    )
    conn.commit()
    updated = get_candidate_asset(conn, candidate_id)
    if not updated:
        raise HTTPException(status_code=404, detail="candidate CAD asset not found")
    return updated
```

- [ ] **Step 5: Add route**

In `backend/app/main.py`:

```python
@app.patch("/api/cad/candidates/{candidate_id}/spec")
def cad_candidate_patch_spec(candidate_id: int, payload: CandidateCadSpecPatchRequest) -> dict:
    conn = get_connection(DB_PATH)
    try:
        candidate = patch_candidate_spec(
            conn,
            candidate_id,
            parameters=payload.parameters,
            component_keys=payload.component_keys,
            review_notes=payload.review_notes,
        )
        return {"candidate": candidate}
    finally:
        conn.close()
```

- [ ] **Step 6: Run test**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_candidate_cad_spec_can_be_patched_and_regenerated -q
```

Expected: PASS.

---

## Task 5: Candidate Promotion Into CAD Workbench

**Files:**

- Create: `backend/app/cad_pipeline/promotion.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/schemas.py`
- Modify: `tests/test_candidate_cad_final_pipeline.py`

- [ ] **Step 1: Write failing test**

Append:

```python
def test_approved_candidate_can_be_promoted_to_cad_workbench_model() -> None:
    candidate = client.get("/api/cad/candidates").json()["candidates"][0]
    candidate_id = candidate["id"]
    client.post(
        f"/api/cad/candidates/{candidate_id}/review",
        json={"status": "approved_candidate", "reviewer": "ME-R2", "notes": "审核通过，可作为候选结构链资产。"},
    )
    response = client.post(
        f"/api/cad/candidates/{candidate_id}/promote",
        json={"model_title": "ISG80-160 泵密封区候选 CAD", "component_binding_mode": "candidate_component_key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["promotion"]["status"] == "promoted_standard_candidate"
    assert body["promotion"]["model_id"].startswith("candidate-cad-")
    models = client.get("/api/3d/models?equipment=pump").json()["models"]
    assert any(item["id"] == body["promotion"]["model_id"] for item in models)
```

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_approved_candidate_can_be_promoted_to_cad_workbench_model -q
```

Expected: FAIL because promote endpoint is missing.

- [ ] **Step 3: Add schema**

In `backend/app/schemas.py`:

```python
class CandidateCadPromoteRequest(BaseModel):
    model_title: str
    component_binding_mode: str = "candidate_component_key"
```

- [ ] **Step 4: Implement promotion**

Create `backend/app/cad_pipeline/promotion.py`:

```python
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from fastapi import HTTPException


def promote_candidate_to_model(conn: sqlite3.Connection, candidate: dict[str, Any], *, model_title: str, component_binding_mode: str) -> dict[str, Any]:
    if candidate.get("status") != "approved_candidate":
        raise HTTPException(status_code=400, detail="candidate must be approved before promotion")
    model_id = f"candidate-cad-{candidate['id']:04d}"
    manifest = candidate.get("artifact_manifest") or {}
    glb_path = ((manifest.get("cad_files") or {}).get("glb") or {}).get("path", "")
    sidecar = {
        "binding_mode": component_binding_mode,
        "component_keys": candidate.get("cad_spec", {}).get("component_keys", []),
        "not_for_measurement": True,
    }
    now = datetime.utcnow().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO standard_3d_models
        (id, equipment, model_code, title, source_type, mesh_path, processed_mesh_path,
         viewer_mode, asset_status, license_json, node_bindings_json, created_at)
        VALUES (?, ?, ?, ?, 'candidate_cad', ?, ?, 'candidate_glb', 'candidate_reviewed', ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          title=excluded.title,
          mesh_path=excluded.mesh_path,
          processed_mesh_path=excluded.processed_mesh_path,
          node_bindings_json=excluded.node_bindings_json,
          asset_status=excluded.asset_status
        """,
        (
            model_id,
            candidate["equipment"],
            candidate.get("model", ""),
            model_title,
            glb_path,
            glb_path,
            json.dumps({"id": "candidate-review", "name": "Reviewed candidate asset"}, ensure_ascii=False),
            json.dumps(sidecar, ensure_ascii=False),
            now,
        ),
    )
    return {"status": "promoted_standard_candidate", "model_id": model_id, "viewer_mode": "candidate_glb"}
```

- [ ] **Step 5: Add route**

In `backend/app/main.py`:

```python
@app.post("/api/cad/candidates/{candidate_id}/promote")
def cad_candidate_promote(candidate_id: int, payload: CandidateCadPromoteRequest) -> dict:
    conn = get_connection(DB_PATH)
    try:
        candidate = get_candidate_asset(conn, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="candidate CAD asset not found")
        promotion = promote_candidate_to_model(
            conn,
            candidate,
            model_title=payload.model_title,
            component_binding_mode=payload.component_binding_mode,
        )
        conn.execute(
            "UPDATE candidate_cad_assets SET status = 'promoted_standard_asset', promotion_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(promotion, ensure_ascii=False), datetime.utcnow().isoformat(timespec="seconds"), candidate_id),
        )
        conn.commit()
        return {"promotion": promotion}
    finally:
        conn.close()
```

- [ ] **Step 6: Run test**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py::test_approved_candidate_can_be_promoted_to_cad_workbench_model -q
```

Expected: PASS.

---

## Task 6: Frontend Review Workbench

**Files:**

- Modify: `frontend/index.html`
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Create: `tests/test_candidate_cad_frontend.py`

- [ ] **Step 1: Write failing frontend static test**

Create `tests/test_candidate_cad_frontend.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_candidate_cad_final_workbench_controls_are_visible() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert "候选 CAD 审核工位" in html
    assert "多视角渲染" in html
    assert "编辑 CAD spec" in html
    assert "晋升为结构链资产" in html
    assert "patchCandidateCadSpec" in js
    assert "promoteCandidateCad" in js
    assert ".candidate-cad-review-workbench" in css
```

- [ ] **Step 2: Verify failure**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_frontend.py -q
```

Expected: FAIL because final workbench strings are missing.

- [ ] **Step 3: Add frontend state and actions**

In `frontend/app.js` data:

```js
candidateCadSpecDraft: "",
candidateCadSelectedId: "",
```

Add methods:

```js
selectCandidateCad(item) {
  this.candidateCadSelectedId = item.id;
  this.candidateCadSpecDraft = JSON.stringify(item.editable_spec || item.cad_spec || {}, null, 2);
},
async patchCandidateCadSpec() {
  if (!this.candidateCadSelectedId) return;
  const parsed = JSON.parse(this.candidateCadSpecDraft || "{}");
  await this.api(`/api/cad/candidates/${this.candidateCadSelectedId}/spec`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parameters: parsed.parameters || {}, component_keys: parsed.component_keys || [], review_notes: "前端人工修正 CAD spec" }),
  });
  await this.refreshAll();
},
async promoteCandidateCad(id) {
  const item = (this.candidateCadAssets || []).find((asset) => asset.id === id);
  await this.api(`/api/cad/candidates/${id}/promote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_title: `${item?.model || "候选"} CAD 结构链资产`, component_binding_mode: "candidate_component_key" }),
  });
  await this.refreshAll();
},
```

- [ ] **Step 4: Add HTML section**

In `frontend/index.html`, inside the candidate CAD panel, add:

```html
<div class="candidate-cad-review-workbench" v-if="latestCandidateCadAsset">
  <div>
    <span class="panel-kicker">候选 CAD 审核工位</span>
    <h3>编辑 CAD spec</h3>
    <textarea v-model="candidateCadSpecDraft" rows="12" @focus="selectCandidateCad(latestCandidateCadAsset)"></textarea>
    <button type="button" @click="patchCandidateCadSpec">保存修正</button>
  </div>
  <div>
    <h3>多视角渲染</h3>
    <div class="candidate-render-grid">
      <img v-for="view in ['front','side','top','iso']" :src="candidateCadFileUrl(latestCandidateCadAsset, 'preview')" :alt="view + ' render'" />
    </div>
    <button type="button" @click="promoteCandidateCad(latestCandidateCadAsset.id)">晋升为结构链资产</button>
  </div>
</div>
```

- [ ] **Step 5: Add CSS**

In `frontend/styles.css`:

```css
.candidate-cad-review-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 14px;
  margin-top: 14px;
  border-top: 1px solid #d7e5e1;
  padding-top: 14px;
}

.candidate-cad-review-workbench textarea {
  width: 100%;
  resize: vertical;
  border: 1px solid #cbd8df;
  border-radius: 7px;
  padding: 10px;
  font-family: Consolas, monospace;
  font-size: 12px;
}

.candidate-render-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.candidate-render-grid img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: contain;
  border: 1px solid #dce7ea;
  border-radius: 7px;
  background: #f8fbfa;
}
```

- [ ] **Step 6: Run frontend test**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_frontend.py -q
node --check frontend\app.js
```

Expected: PASS.

---

## Task 7: Real Rendering Upgrade

**Files:**

- Modify: `backend/app/cad_pipeline/renderer.py`
- Modify: `requirements-3d.txt`
- Create: `scripts/render_candidate_cad.py`
- Modify: `tests/test_candidate_cad_final_pipeline.py`

- [ ] **Step 1: Add dependency policy**

Modify `requirements-3d.txt`:

```text
cadquery>=2.5
```

Do not force Blender or FreeCAD into pip; document them as system tools.

- [ ] **Step 2: Add render script**

Create `scripts/render_candidate_cad.py`:

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.cad_pipeline.renderer import render_candidate_artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    result = render_candidate_artifacts(Path(args.out), spec=spec)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Replace placeholder renderer when CadQuery exists**

In `renderer.py`, implement:

```python
def _try_cadquery_export(artifact_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    try:
        import cadquery as cq
        from cadquery import exporters
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    # Build a conservative generic block/cylinder model from spec parameters.
    equipment = spec.get("equipment", "general")
    params = spec.get("parameters", {})
    if equipment == "pump":
        model = cq.Workplane("XY").box(params.get("body_length", 150), params.get("body_height", 96), 60).edges("|Z").fillet(8)
    elif equipment == "bearing":
        model = cq.Workplane("XY").circle(params.get("outer_diameter", 52) / 2).circle(params.get("inner_diameter", 25) / 2).extrude(params.get("width", 15))
    elif equipment == "motor":
        model = cq.Workplane("YZ").circle(params.get("body_diameter", 92) / 2).extrude(params.get("body_length", 180))
    else:
        model = cq.Workplane("XY").box(params.get("block_width", 120), 70, params.get("block_height", 130))
    exporters.export(model, str(artifact_dir / "candidate.step"))
    exporters.export(model, str(artifact_dir / "candidate.stl"))
    return {"ok": True}
```

Call this before placeholder creation. If it fails, keep placeholder files and include error in `runtime_report`.

- [ ] **Step 4: Test render script**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\render_candidate_cad.py --spec data\cad_candidates\candidate_0001_pump\cad_spec.json --out tmp\candidate_render_test
```

Expected:

- If CadQuery is installed: STEP/STL are real exported files.
- If not installed: placeholders are produced and runtime report says `code_only` or `partial_render`.

---

## Task 8: Documentation And Demo Script

**Files:**

- Create: `docs/CANDIDATE_CAD_FINAL_PIPELINE.md`
- Modify: `docs/DEMO_TEST_DATA.md`
- Modify: `docs/DEMO_SCRIPT.md`

- [ ] **Step 1: Create final documentation**

Create `docs/CANDIDATE_CAD_FINAL_PIPELINE.md`:

```markdown
# 现场照片驱动的候选 CAD 资产沉淀链路

## 定位

本功能不是单张照片精密反求 CAD，而是将现场照片转化为可审核、可编辑、可回滚的候选 CAD 资产。

## 最终链路

现场照片 -> VLM/OCR 观察 -> CAD spec -> CadQuery/OpenSCAD/FreeCAD 生成 -> 多视角渲染 -> VLM/规则对比 -> 人工审核 -> 候选资产池 -> 结构链资产。

## 风险边界

- 不用于尺寸测量。
- 不用于制造加工。
- 不用于安全放行。
- 必须由机械审核人批准。

## 答辩价值

它体现结构链不是静态模型库，而是可以从现场资料持续沉淀。
```

- [ ] **Step 2: Add demo script section**

In `docs/DEMO_SCRIPT.md`, add:

```markdown
## 候选 CAD 资产沉淀演示

1. 上传泵机械密封泄漏照片。
2. 系统提取机械密封、泵轴、泵体、法兰孔位等观察结果。
3. 生成 CAD spec 和候选代码。
4. 展示 STEP/STL/GLB/多视角渲染。
5. 人工修正 CAD spec 中的尺寸来源和 component_key。
6. 审核通过后进入候选 CAD 资产池。
7. 晋升为结构链资产，在 CAD 工位中按 SOP 高亮。
8. 强调非测量、非制造、非安全放行边界。
```

---

## Final Verification

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_candidate_cad_final_pipeline.py tests\test_candidate_cad_frontend.py tests\test_api.py::test_candidate_cad_asset_pipeline_from_visual_asset -q
node --check frontend\app.js
.\.venv\Scripts\python.exe scripts\verify_cad_pipeline_runtime.py
```

Expected:

- Candidate CAD final tests pass.
- Frontend static checks pass.
- Existing v1 API test still passes.
- Runtime report clearly says whether the environment is `real_render`, `partial_render`, or `code_only`.

## Rollout Criteria

Ship to main demo only when:

- At least one pump or bearing candidate produces visible multi-view renders.
- Candidate asset has `CAD spec`, `CadQuery`, `OpenSCAD`, `STEP/STL/GLB`, render views, compare report, and review record.
- UI clearly labels it as candidate and non-measurement.
- Approved candidate can appear in CAD workbench model list.

Do not claim:

- Photo-to-precision-CAD.
- Automatic manufacturable CAD.
- Safety release from generated CAD.

Claim:

- “现场照片驱动的候选 CAD 资产沉淀链路”。
- “结构链可以从现场资料持续补齐，但必须经过机械审核。”
