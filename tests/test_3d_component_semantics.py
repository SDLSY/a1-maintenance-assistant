from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_3d_component_semantics import audit  # noqa: E402


def test_3d_component_semantics_audit_passes() -> None:
    report = audit()
    assert report["status"] == "passed", report["errors"]


def test_three_workbench_procedural_shapes_use_canonical_keys() -> None:
    source = (ROOT / "frontend" / "three-workbench.js").read_text(encoding="utf-8")
    assert 'this.torus("front_bearing"' not in source
    assert 'this.torus("mechanical_seal"' not in source
    assert 'this.box("rotor_shaft"' not in source
    assert 'this.box("stator_winding"' not in source
    assert 'this.box("cylinder",' not in source


def test_local_glb_uses_visible_semantic_overlay_for_all_equipment() -> None:
    source = (ROOT / "frontend" / "three-workbench.js").read_text(encoding="utf-8")
    assert "addSemanticEquipmentOverlay(model)" in source
    assert "addSemanticBearingOverlay(model)" not in source
    assert 'if (model?.equipment === "bearing" && !this.isGeneratedCandidateModel(model))' in source
    assert 'SECTION_SUPPORTED_EQUIPMENT = new Set(["bearing", "pump", "motor", "engine"])' in source
    assert "this.sectionEnabled = Boolean(enabled && SECTION_SUPPORTED_EQUIPMENT.has(equipment))" in source
    assert 'this.currentModel?.equipment === "bearing")' not in source
    assert "this.sectionEnabled = false" in source
    assert 'if (equipment === "motor")' in source
    assert 'this.torus("front_bearing_end"' not in source
    assert 'this.cylinder("front_bearing_end"' in source
    assert 'if (equipment === "pump")' in source
    assert 'this.torus("pump_seal_zone"' not in source
    assert 'this.cylinder("pump_seal_zone"' in source
    assert 'if (equipment === "engine")' in source
    assert 'this.box("spark_plug"' in source
    assert 'this.torus("water_pump"' not in source
    assert "isAuxiliaryMarkerNode(name)" in source
    assert "captureMarkerAnchor(node, key)" in source
    assert "VIEWPORT_GROUP_OFFSET_Y" in source
    assert "this.group.position.set(0, VIEWPORT_GROUP_OFFSET_Y, 0)" in source
    assert "fitToContents()" in source
    assert "sceneContentBox()" in source
    assert "node.userData?.hotspotMarker || node.userData?.labelAnchor || node.userData?.sectionPlane" in source
    assert "new THREE.Box3().setFromObject(this.group)" in source
    assert "this.cameraTarget.copy(center)" in source


def test_three_workbench_anchors_hotspots_to_visible_semantic_parts() -> None:
    source = (ROOT / "frontend" / "three-workbench.js").read_text(encoding="utf-8")
    assert "COMPONENT_LABEL_ANCHORS" in source
    assert "namedMarkerAnchors" in source
    assert "captureNamedMarkerAnchors(root)" in source
    assert "markerComponentKey(name)" in source
    assert "component?.geometry?.source_node" in source
    assert "visibleHotspotComponents(model)" in source
    assert "const highlightedKeys = Object.keys(this.highlightByKey)" in source
    assert "DEFAULT_VISIBLE_COMPONENT_KEYS" in source
    assert "RELIABLE_HIGHLIGHT_COMPONENT_KEYS" in source
    assert "NON_BEARING_LABEL_CONFIDENCE_THRESHOLD" in source
    assert 'motor: ["front_bearing_end", "end_cover", "output_shaft", "terminal_connector"]' in source
    assert 'pump: ["pump_head", "inlet_outlet", "motor_body", "pump_shaft"]' in source
    assert 'engine: ["spark_plug", "cylinder_head", "cylinder_block", "cooling_fins"]' in source
    assert "if (highlighted.length) return highlighted" in source
    assert "anchorSource(componentKey)" in source
    assert "anchorClass(componentKey)" in source
    assert "模型内置预标" in source
    assert "人工校准锚点" in source
    assert "calibratedAnchors" in source
    assert "setCalibrationMode" in source
    assert "handleCalibrationPointer(event)" in source
    assert "this.raycaster.intersectObjects" in source
    assert "window.localStorage?.setItem" in source
    assert "this.hasCalibratedAnchor(component.component_key)" in source
    for key in [
        "front_bearing_end",
        "terminal_connector",
        "mounting_flange",
        "pump_seal_zone",
        "pump_head",
        "motor_body",
        "outer_ring",
        "rolling_elements",
        "spark_plug",
        "crankcase",
        "cooling_fins",
        "wiring_harness",
    ]:
        assert f"{key}:" in source
    assert "const position = this.componentAnchorPosition(component)" in source
    assert "const markerAnchor = this.namedMarkerAnchors.get(sourceKey || key) || this.namedMarkerAnchors.get(key)" in source
    assert "this.meshes.get(key)" in source
    assert "Number.isFinite(hotspot.x) ? hotspot.x : 0" in source
    assert "placedLabels" in source
    assert "while (placedLabels.some" in source
    assert "translate(${left}px, ${top}px)" in source


def test_spatial_hotspot_detail_does_not_reflow_label_layout() -> None:
    source = (ROOT / "frontend" / "three-workbench.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert "el.dataset.detailPlacement" in source
    assert "el.dataset.detailVertical" in source
    assert "left + 236 > rect.width - 6" in source
    assert "top + height + 104 > rect.height - 6" in source
    assert "contain: layout style" in css
    assert "max-width 0.14s ease" not in css
    assert ".spatial-hotspot-label.expanded span" in css
    assert "position: absolute" in css
    assert '[data-detail-placement="right"]' in css
    assert '[data-detail-vertical="top"]' in css


def test_three_workbench_semantic_overlay_covers_authorized_model_components() -> None:
    source = (ROOT / "frontend" / "three-workbench.js").read_text(encoding="utf-8")
    for shape in [
        'this.box("terminal_connector"',
        'this.box("mounting_flange"',
        'this.cylinder("pump_head"',
        'this.cylinder("motor_body"',
        'this.cylinder("inlet_outlet"',
        'this.box("mounting_bracket"',
        'this.box("crankcase"',
        'this.box("cooling_fins"',
        'this.box("intake_exhaust_ports"',
        'this.box("wiring_harness"',
    ]:
        assert shape in source
    assert '["bearing", "pump", "motor", "engine"].includes(equipment)' in source


def test_spatial_workbench_exposes_manual_calibration_controls() -> None:
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert "calibration-toolbar" in index_html
    assert "spatialCalibrationComponentKey" in index_html
    assert "toggleSpatialCalibration" in index_html
    assert "spatialCalibrationComponents" in app
    assert "applySpatialCalibrationMode" in app
    assert "calibration-toolbar button.active" in css


def test_generated_cad_calibration_uses_generated_components() -> None:
    app = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "const componentMap = new Map()" in app
    assert "(spec.components || []).forEach" in app
    assert "components: Array.from(componentMap.values())" in app
    assert 'this.spatialModelSource === "generated"' in app
    assert "this.generatedCadModel?.components || []" in app
    assert "ensureSpatialCalibrationComponentKey" in app
    assert "const calibrationKey = this.ensureSpatialCalibrationComponentKey()" in app


def test_spatial_evidence_cards_use_grid_layout() -> None:
    css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    assert ".pro-evidence-panel .pro-component-card" in css
    assert "grid-template-columns: minmax(0, 1fr) auto" in css


def test_spatial_viewer_rebuilds_when_vue_recreates_canvas_container() -> None:
    source = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "staleViewer" in source
    assert "this.spatialViewer.container !== container" in source
    assert "!viewerCanvas.isConnected" in source
    assert "!container.contains(viewerCanvas)" in source
    assert "this.spatialViewer.dispose?.()" in source


def test_spatial_workbench_equipment_switch_ignores_stale_guidance() -> None:
    source = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "changeSpatialEquipment" in source
    assert "matchesCurrentEquipment" in source
    assert "guidance.equipment === this.query.equipment" in source
    assert "guidanceMatchesCurrentEquipment" in source
    assert '@change="changeSpatialEquipment"' in index_html


def test_spatial_workbench_does_not_expose_explode_view() -> None:
    source = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "爆炸视图" not in index_html
    assert "toggleSpatialExplode" not in source
    assert "spatialExploded" not in source
    assert "setExploded" not in source


def test_three_workbench_no_longer_exposes_explosion_api() -> None:
    source = (ROOT / "frontend" / "three-workbench.js").read_text(encoding="utf-8")
    assert "setExploded" not in source
    assert "applyExplode" not in source
    assert "EXPLODE_OFFSETS" not in source
    assert "EXPLODE_SCALE" not in source
    assert "semanticExplodeOffset" not in source
