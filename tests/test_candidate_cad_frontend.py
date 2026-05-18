from __future__ import annotations

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
    assert "openCandidateCadViewer" in js
    assert "candidateCadLightbox" in js
    assert "/api/cad/runtime" in js
    assert ".candidate-cad-review-workbench" in css
    assert ".cad-viewer-modal" in css
    assert "CAD 多视角详情" in html
    assert "tri-mro-traceable-workbench-20260518-v3" in html
    assert '@click.prevent.stop="openCandidateCadViewer(item, \'iso\')"' in html
    assert "candidate-render-open" in html
    assert "rotateCandidateCadViewer" in js
    assert "candidateCadViewerImageStyle" in js
    assert "cad-viewer-rotate-tools" in html
    assert "cad-viewer-mode-tabs" in html
    assert "cad-viewer-glb-stage" in html
    assert "setCandidateCadViewerMode" in js
    assert "renderCandidateCadGlbViewer" in js
    assert "candidateCadViewerGlbUrl" in js
    assert "THREE.DoubleSide" in js
    assert "new THREE.MeshStandardMaterial" in js
    assert "__candidateCadGlbDiagnostics" in js
    assert "Vue.markRaw" in js
    assert "candidateCadGlbViewerToken" in js
    assert "preserveDrawingBuffer: true" in js
    assert 'renderMode: "on_demand"' in js
    assert "requestRender" in js
    assert "computeVertexNormals" in js
