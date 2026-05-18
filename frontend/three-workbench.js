(function () {
  const COLORS = {
    steel: 0x8191a3,
    dark: 0x142534,
    blue: 0x2f6f9f,
    teal: 0x168a7a,
    amber: 0xd99022,
    danger: 0xc73a3a,
    ghost: 0xd7e0e8,
    section: 0x50a6c8,
  };

  const COMPONENT_LABEL_ANCHORS = {
    outer_ring: [-0.2, 1.02, 0.24],
    inner_ring: [0.38, 0.5, 0.2],
    rolling_elements: [-0.72, 0.58, 0.26],
    cage: [0.12, 0.78, 0.22],
    seal_pair: [0.86, 0.38, 0.3],
    seal_lubrication: [0.86, 0.38, 0.3],
    front_bearing_end: [0.66, 0.02, 0.2],
    end_cover: [0.78, 0.02, 0.32],
    output_shaft: [1.0, 0.0, 0.0],
    motor_housing: [0.0, 0.0, 0.46],
    terminal_connector: [-0.44, 0.56, 0.52],
    mounting_flange: [0.58, -0.56, -0.16],
    pump_seal_zone: [0.52, 0.05, 0.26],
    pump_head: [0.36, -0.12, 0.38],
    pump_casing: [0.36, -0.12, 0.38],
    impeller: [0.02, 0.0, 0.12],
    pump_shaft: [0.02, 0.0, 0.12],
    motor_body: [-0.42, 0.0, 0.28],
    inlet_outlet: [0.76, 0.42, 0.44],
    mounting_bracket: [-0.1, -0.56, -0.1],
    spark_plug: [0.24, 0.76, 0.46],
    cylinder_head: [-0.08, 0.38, 0.36],
    cylinder_block: [0.02, 0.03, 0.16],
    crankcase: [-0.04, -0.34, -0.24],
    cooling_fins: [-0.38, 0.5, 0.5],
    intake_exhaust_ports: [0.72, 0.08, 0.18],
    wiring_harness: [-0.62, 0.1, 0.22],
    starter_motor: [-0.48, -0.18, 0.04],
    water_pump: [0.7, -0.2, 0.08],
  };
  const DEFAULT_VISIBLE_COMPONENT_KEYS = {
    bearing: ["outer_ring", "inner_ring", "rolling_elements", "cage", "seal_pair"],
    motor: ["front_bearing_end", "end_cover", "output_shaft", "terminal_connector"],
    pump: ["pump_head", "inlet_outlet", "motor_body", "pump_shaft"],
    engine: ["spark_plug", "cylinder_head", "cylinder_block", "cooling_fins"],
  };
  const RELIABLE_HIGHLIGHT_COMPONENT_KEYS = {
    bearing: ["outer_ring", "inner_ring", "rolling_elements", "cage", "seal_pair"],
    motor: ["front_bearing_end", "end_cover", "output_shaft", "motor_housing", "terminal_connector", "mounting_flange"],
    pump: ["pump_seal_zone", "pump_head", "impeller", "pump_shaft", "pump_casing", "motor_body", "inlet_outlet", "mounting_bracket"],
    engine: ["spark_plug", "cylinder_head", "cylinder_block", "crankcase", "cooling_fins", "intake_exhaust_ports", "wiring_harness", "starter_motor", "water_pump"],
  };
  const NON_BEARING_LABEL_CONFIDENCE_THRESHOLD = 0.4;
  const SECTION_SUPPORTED_EQUIPMENT = new Set(["bearing", "pump", "motor", "engine"]);
  const VIEWPORT_GROUP_OFFSET_Y = 0.42;
  const AUXILIARY_ANCESTOR_SENTINEL = "__auxiliary_construction__";

  class A1ThreeWorkbench {
    constructor(container) {
      this.container = container;
      this.scene = null;
      this.camera = null;
      this.renderer = null;
      this.group = null;
      this.labelLayer = null;
      this.externalFrame = null;
      this.meshes = new Map();
      this.labels = [];
      this.namedMarkerAnchors = new Map();
      this.calibratedAnchors = new Map();
      this.highlightByKey = {};
      this.currentModel = {};
      this.loadedRoot = null;
      this.sectionPlaneMesh = null;
      this.clipPlane = null;
      this.sectionEnabled = false;
      this.focusedComponentKey = "";
      this.expandedLabelKey = "";
      this.cameraTarget = null;
      this.dragging = false;
      this.lastPointer = { x: 0, y: 0 };
      this.raycaster = null;
      this.calibrationMode = false;
      this.calibrationComponentKey = "";
      this.calibrationCallback = null;
      this.zoom = 5.2;
      this.raf = 0;
      this.loadToken = 0;
      this.resizeObserver = null;
      this.init();
    }

    init() {
      if (!window.THREE) {
        this.container.innerHTML = "<div class='spatial-viewer-fallback'>Three.js 未加载，无法显示 3D 模型。</div>";
        return;
      }
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0xf4f7fa);
      this.camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
      this.cameraTarget = new THREE.Vector3(0, VIEWPORT_GROUP_OFFSET_Y, 0);
      this.camera.position.set(3.8, 2.65, this.zoom);
      this.camera.lookAt(this.cameraTarget);
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.localClippingEnabled = true;
      this.raycaster = new THREE.Raycaster();

      this.container.innerHTML = "";
      this.container.classList.add("spatial-canvas-mounted");
      this.container.appendChild(this.renderer.domElement);
      this.labelLayer = document.createElement("div");
      this.labelLayer.className = "spatial-label-layer";
      this.container.appendChild(this.labelLayer);

      const ambient = new THREE.AmbientLight(0xffffff, 0.74);
      const key = new THREE.DirectionalLight(0xffffff, 0.95);
      key.position.set(5, 6, 4);
      const rim = new THREE.DirectionalLight(0x9bd7e8, 0.45);
      rim.position.set(-4, 2, -3);
      this.scene.add(ambient, key, rim);

      this.group = new THREE.Group();
      this.group.position.set(0, VIEWPORT_GROUP_OFFSET_Y, 0);
      this.scene.add(this.group);
      this.addGrid();
      this.bindEvents();
      this.resize();
      this.animate();
    }

    addGrid() {
      const grid = new THREE.GridHelper(6.2, 18, 0x9fb0bf, 0xd8e1e8);
      grid.position.y = -1.18;
      this.scene.add(grid);
      const plane = new THREE.Mesh(
        new THREE.CircleGeometry(2.55, 80),
        new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.35, side: THREE.DoubleSide }),
      );
      plane.rotation.x = -Math.PI / 2;
      plane.position.y = -1.17;
      this.scene.add(plane);
    }

    bindEvents() {
      const canvas = this.renderer.domElement;
      canvas.addEventListener("pointerdown", (event) => {
        if (this.handleCalibrationPointer(event)) return;
        this.dragging = true;
        this.lastPointer = { x: event.clientX, y: event.clientY };
        canvas.setPointerCapture(event.pointerId);
      });
      canvas.addEventListener("pointermove", (event) => {
        if (!this.dragging || !this.group) return;
        const dx = event.clientX - this.lastPointer.x;
        const dy = event.clientY - this.lastPointer.y;
        this.group.rotation.y += dx * 0.008;
        this.group.rotation.x += dy * 0.004;
        this.group.rotation.x = Math.max(-0.85, Math.min(0.85, this.group.rotation.x));
        this.lastPointer = { x: event.clientX, y: event.clientY };
      });
      canvas.addEventListener("pointerup", () => {
        this.dragging = false;
      });
      canvas.addEventListener(
        "wheel",
        (event) => {
          event.preventDefault();
          this.zoom = Math.max(3.0, Math.min(7.6, this.zoom + Math.sign(event.deltaY) * 0.28));
          this.applyCameraDistance(this.zoom);
        },
        { passive: false },
      );
      this.resizeObserver = new ResizeObserver(() => this.resize());
      this.resizeObserver.observe(this.container);
    }

    material(color, options = {}) {
      return new THREE.MeshStandardMaterial({
        color,
        roughness: options.roughness ?? 0.42,
        metalness: options.metalness ?? 0.28,
        transparent: Boolean(options.transparent),
        opacity: options.opacity ?? 1,
        emissive: options.emissive || 0x000000,
        emissiveIntensity: options.emissiveIntensity || 0,
        side: options.side || THREE.FrontSide,
        depthWrite: options.depthWrite ?? true,
      });
    }

    escapeHtml(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }

    toneColor(tone) {
      if (tone === "danger") return COLORS.danger;
      if (tone === "warning") return COLORS.amber;
      return COLORS.teal;
    }

    componentTone(key) {
      return this.highlightByKey[key]?.tone || "info";
    }

    isHighlighted(key) {
      return Boolean(this.highlightByKey[key]) || this.focusedComponentKey === key;
    }

    componentMaterial(key, baseColor, options = {}) {
      const highlighted = this.isHighlighted(key);
      const color = highlighted ? this.toneColor(this.componentTone(key)) : baseColor;
      return this.material(color, {
        ...options,
        emissive: highlighted ? color : 0x000000,
        emissiveIntensity: highlighted ? 0.18 : 0,
      });
    }

    clear() {
      this.loadToken += 1;
      if (this.externalFrame) {
        this.externalFrame.remove();
        this.externalFrame = null;
      }
      if (this.renderer?.domElement) this.renderer.domElement.style.display = "";
      if (this.labelLayer) {
        this.labelLayer.style.display = "";
        this.labelLayer.innerHTML = "";
      }
      while (this.group?.children.length) this.group.remove(this.group.children[0]);
      if (this.group) this.group.position.set(0, VIEWPORT_GROUP_OFFSET_Y, 0);
      this.meshes.clear();
      this.labels = [];
      this.namedMarkerAnchors.clear();
      this.loadedRoot = null;
      this.sectionPlaneMesh = null;
      this.clipPlane = null;
      this.sectionEnabled = false;
      this.expandedLabelKey = "";
      if (this.renderer) this.renderer.localClippingEnabled = true;
    }

    showLoading(message) {
      if (!this.labelLayer) return;
      this.labelLayer.innerHTML = `<div class="spatial-loader">${this.escapeHtml(message)}</div>`;
    }

    showExternalEmbed(model, highlightedComponents = []) {
      if (!model?.embed_url) return false;
      if (this.renderer?.domElement) this.renderer.domElement.style.display = "none";
      if (this.labelLayer) this.labelLayer.style.display = "none";

      const chips = (highlightedComponents || [])
        .slice(0, 4)
        .map((item) => `<span class="tone-${this.escapeHtml(item.tone || "info")}">${this.escapeHtml(item.label)} ${Math.round((item.confidence || 0) * 100)}%</span>`)
        .join("");
      const preview = model.preview_path
        ? `<img class="spatial-external-preview" src="${this.escapeHtml(model.preview_path)}" alt="${this.escapeHtml(model.title || "3D model preview")}" />`
        : "";
      const wrapper = document.createElement("div");
      wrapper.className = "spatial-external-viewer";
      wrapper.innerHTML = `
        <div class="spatial-external-toolbar">
          <div>
            <strong>${this.escapeHtml(model.title || "外部 3D 模型")}</strong>
            <span>${this.escapeHtml(model.asset_status || "external_embed")}</span>
          </div>
          <a href="${this.escapeHtml(model.source_url || model.embed_url)}" target="_blank" rel="noopener">来源/署名</a>
        </div>
        <iframe title="${this.escapeHtml(model.title || "external 3D model")}" src="${this.escapeHtml(model.embed_url)}" allow="autoplay; fullscreen; xr-spatial-tracking" loading="eager" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
        ${preview}
        <div class="spatial-external-foot">
          <p>${this.escapeHtml(model.attribution || "外部 3D 资产，仅作增强展示。")}</p>
          <div>${chips || "<span>等待部件定位</span>"}</div>
        </div>
      `;
      this.container.appendChild(wrapper);
      this.externalFrame = wrapper;
      return true;
    }

    setModel(model, highlightedComponents = []) {
      if (!this.group) return;
      this.clear();
      this.currentModel = model || {};
      this.loadCalibratedAnchors();
      this.highlightByKey = Object.fromEntries((highlightedComponents || []).map((item) => [item.component_key, item]));
      const isLocalGlb = this.currentModel.viewer_mode === "local_glb" || this.currentModel.processed_mesh_url || String(this.currentModel.mesh_path || "").endsWith(".glb");
      const hasSemanticOverlay = this.currentModel.viewer_mode === "semantic_overlay" || this.currentModel.node_bindings?.semantic_sidecar_ready;
      if (isLocalGlb && this.showLocalGlb(this.currentModel)) return;
      if (hasSemanticOverlay) {
        this.showProcedural(this.currentModel);
        return;
      }
      if (this.currentModel.source_type === "external_embed" || this.currentModel.embed_url) {
        if (this.showExternalEmbed(this.currentModel, highlightedComponents)) return;
      }
      this.showProcedural(this.currentModel);
    }

    showLocalGlb(model) {
      const path = model.processed_mesh_url || model.mesh_path;
      const Loader = window.THREE?.GLTFLoader;
      if (!path || !Loader) return false;
      const token = this.loadToken;
      this.showLoading("正在加载本地授权 GLB 模型...");
      const loader = new Loader();
      loader.load(
        path,
        (gltf) => {
          if (token !== this.loadToken) return;
          this.labelLayer.innerHTML = "";
          const root = gltf.scene || gltf.scenes?.[0];
          if (!root) {
            this.showProcedural(model);
            return;
          }
          this.loadedRoot = root;
          this.prepareLoadedModel(root);
          this.captureNamedMarkerAnchors(root);
          this.pruneAuxiliaryMarkers(root);
          this.group.add(root);
          if (model?.equipment === "bearing" && !this.isGeneratedCandidateModel(model)) {
            this.addSemanticEquipmentOverlay(model);
          }
          this.addComponentHotspots(model);
          this.group.rotation.set(-0.12, -0.62, 0);
          this.applySection();
          this.fitToContents();
          this.updateLabels();
        },
        undefined,
        () => {
          if (token !== this.loadToken) return;
          this.labelLayer.innerHTML = "";
          this.showProcedural(model);
        },
      );
      return true;
    }

    prepareLoadedModel(root) {
      const box = this.modelContentBox(root);
      const size = new THREE.Vector3();
      const center = new THREE.Vector3();
      box.getSize(size);
      box.getCenter(center);
      const maxSize = Math.max(size.x, size.y, size.z) || 1;
      const targetSize = this.currentModel?.equipment === "pump" ? 4.1 : 2.35;
      const scale = targetSize / maxSize;
      root.scale.setScalar(scale);
      root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
      const generatedCandidateModel = this.isGeneratedCandidateModel();
      root.traverse((node) => {
        const markerKey = this.markerComponentKey(node.name);
        if (this.isAuxiliaryMarkerNode(node.name)) {
          if (markerKey && !this.namedMarkerAnchors.has(markerKey)) this.captureMarkerAnchor(node, markerKey);
          node.userData = { ...node.userData, hotspotMarker: true, auxiliaryMarker: true, componentKey: markerKey };
          node.visible = false;
        }
        if (!node.isMesh) return;
        node.name = node.name || "authorized_cad_mesh";
        const inheritedMarkerKey = this.ancestorMarkerComponentKey(node);
        if (inheritedMarkerKey || this.isAuxiliaryMarkerNode(node.name)) {
          const captureKey = inheritedMarkerKey === AUXILIARY_ANCESTOR_SENTINEL ? "" : inheritedMarkerKey;
          if (captureKey && !this.namedMarkerAnchors.has(captureKey)) this.captureMarkerAnchor(node, captureKey);
          node.userData = { ...node.userData, hotspotMarker: true, auxiliaryMarker: true, componentKey: captureKey };
          node.visible = false;
          return;
        }
        const material = Array.isArray(node.material) ? node.material[0] : node.material;
        const next = material ? material.clone() : this.material(COLORS.steel);
        next.color = next.color || new THREE.Color(COLORS.steel);
        next.color = new THREE.Color(COLORS.steel);
        next.roughness = 0.34;
        next.metalness = 0.38;
        next.transparent = true;
        next.opacity = generatedCandidateModel ? 0.88 : 0.72;
        next.needsUpdate = true;
        node.material = next;
        node.userData = { ...node.userData, baseModelMesh: true };
        node.castShadow = false;
        node.receiveShadow = false;
        if (!generatedCandidateModel) {
          const edges = new THREE.LineSegments(
            new THREE.EdgesGeometry(node.geometry, 28),
            new THREE.LineBasicMaterial({ color: 0x24384a, transparent: true, opacity: 0.32 }),
          );
          edges.position.copy(node.position);
          edges.rotation.copy(node.rotation);
          edges.scale.copy(node.scale);
          node.add(edges);
        }
      });
    }

    modelContentBox(root) {
      const box = new THREE.Box3();
      root.updateMatrixWorld(true);
      root.traverse((node) => {
        if (!node.isMesh) return;
        if (this.isAuxiliaryMarkerNode(node.name) || this.ancestorMarkerComponentKey(node)) return;
        box.expandByObject(node);
      });
      return box.isEmpty() ? new THREE.Box3().setFromObject(root) : box;
    }

    markerComponentKey(name) {
      const match = String(name || "").match(/__([A-Za-z0-9_]+)_marker$/);
      return match ? match[1] : "";
    }

    isGeneratedCandidateModel(model = this.currentModel) {
      const id = String(model?.id || "");
      return model?.source_type === "candidate_cad"
        || model?.cad_bridge?.binding_mode === "generated"
        || model?.node_bindings?.binding_mode === "generated"
        || id.startsWith("cad-candidate-");
    }

    isGeneratedCandidateDecorationNode(name) {
      if (!this.isGeneratedCandidateModel()) return false;
      const normalized = String(name || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
      if (!normalized) return false;
      return /(^|_)(reference|construction|helper|datum|origin|axis|plane|sketch|wire)(_|$)/i.test(normalized)
        || /(^|_)(base|left_foot|right_foot|foot|flange)_candidate$/i.test(normalized)
        || /_candidate_(base|foot|flange)$/i.test(normalized);
    }

    isAuxiliaryMarkerNode(name) {
      const value = String(name || "");
      const normalized = value
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
      return /__([A-Za-z0-9_]+)_marker$/i.test(value)
        || /(^|[_-])(marker|hotspot|anchor|annotation|label)([_-]|$)/i.test(value)
        || /^(origin|x_axis|y_axis|z_axis|xy_plane|xz_plane|yz_plane)(_?\d+)?$/i.test(normalized)
        || /^(origin|xaxis|yaxis|zaxis|xyplane|xzplane|yzplane)(_?\d+)?$/i.test(normalized)
        || this.isGeneratedCandidateDecorationNode(value);
    }

    ancestorMarkerComponentKey(node) {
      let current = node?.parent || null;
      while (current) {
        const key = this.markerComponentKey(current.name);
        if (key) return key;
        if (this.isAuxiliaryMarkerNode(current.name)) return AUXILIARY_ANCESTOR_SENTINEL;
        current = current.parent;
      }
      return "";
    }

    captureMarkerAnchor(node, key) {
      if (!node || !key) return;
      const box = new THREE.Box3().setFromObject(node);
      if (box.isEmpty()) return;
      const center = new THREE.Vector3();
      box.getCenter(center);
      if ([center.x, center.y, center.z].every(Number.isFinite)) {
        this.namedMarkerAnchors.set(key, center.clone());
      }
    }

    captureNamedMarkerAnchors(root) {
      if (!root) return;
      root.updateMatrixWorld(true);
      root.traverse((node) => {
        const key = this.markerComponentKey(node.name);
        const inheritedMarkerKey = node.isMesh ? this.ancestorMarkerComponentKey(node) : "";
        const markerKey = key || inheritedMarkerKey;
        if (!this.isAuxiliaryMarkerNode(node.name) && !inheritedMarkerKey) return;
        const captureKey = markerKey === AUXILIARY_ANCESTOR_SENTINEL ? "" : markerKey;
        if (captureKey && !this.namedMarkerAnchors.has(captureKey)) this.captureMarkerAnchor(node, captureKey);
        node.userData = { ...node.userData, hotspotMarker: true, auxiliaryMarker: true, componentKey: captureKey };
        node.visible = false;
      });
    }

    pruneAuxiliaryMarkers(root) {
      if (!root) return;
      const removable = [];
      root.traverse((node) => {
        if (node.userData?.auxiliaryMarker && node.parent) removable.push(node);
      });
      removable.forEach((node) => node.parent?.remove(node));
    }

    calibrationStorageKey() {
      return `a1.cad.calibration.${this.currentModel?.id || "unknown-model"}`;
    }

    loadCalibratedAnchors() {
      this.calibratedAnchors.clear();
      try {
        const raw = window.localStorage?.getItem(this.calibrationStorageKey());
        const payload = raw ? JSON.parse(raw) : {};
        Object.entries(payload.anchors || payload || {}).forEach(([key, value]) => {
          const point = Array.isArray(value) ? value : [value?.x, value?.y, value?.z];
          if (point.length === 3 && point.every(Number.isFinite)) {
            this.calibratedAnchors.set(key, new THREE.Vector3(point[0], point[1], point[2]));
          }
        });
      } catch {
        this.calibratedAnchors.clear();
      }
    }

    saveCalibratedAnchors() {
      const anchors = {};
      this.calibratedAnchors.forEach((value, key) => {
        anchors[key] = [Number(value.x.toFixed(4)), Number(value.y.toFixed(4)), Number(value.z.toFixed(4))];
      });
      window.localStorage?.setItem(
        this.calibrationStorageKey(),
        JSON.stringify({
          model_id: this.currentModel?.id || "",
          equipment: this.currentModel?.equipment || "",
          updated_at: new Date().toISOString(),
          anchors,
        }),
      );
      return anchors;
    }

    hasCalibratedAnchor(key) {
      return this.calibratedAnchors.has(key);
    }

    setCalibrationMode(options = {}) {
      this.calibrationMode = Boolean(options.enabled);
      this.calibrationComponentKey = options.componentKey || "";
      this.calibrationCallback = typeof options.onChange === "function" ? options.onChange : null;
      this.container?.classList.toggle("spatial-calibration-active", this.calibrationMode);
    }

    handleCalibrationPointer(event) {
      if (!this.calibrationMode || !this.calibrationComponentKey || !this.raycaster || !this.camera || !this.group) return false;
      event.preventDefault();
      event.stopPropagation();
      const rect = this.renderer.domElement.getBoundingClientRect();
      const pointer = new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      this.raycaster.setFromCamera(pointer, this.camera);
      const targets = [];
      const collect = (node) => {
        if (node.isMesh && node.visible !== false && !node.userData?.hotspotMarker && !node.userData?.semanticOverlay && !node.userData?.sectionPlane) {
          targets.push(node);
        }
      };
      if (this.loadedRoot) this.loadedRoot.traverse(collect);
      if (!targets.length) this.group.traverse(collect);
      const hit = this.raycaster.intersectObjects(targets, true)[0];
      if (!hit) return true;
      const local = this.group.worldToLocal(hit.point.clone());
      this.calibratedAnchors.set(this.calibrationComponentKey, local);
      const anchors = this.saveCalibratedAnchors();
      this.redrawHotspots();
      this.calibrationCallback?.({
        model_id: this.currentModel?.id || "",
        equipment: this.currentModel?.equipment || "",
        component_key: this.calibrationComponentKey,
        position: anchors[this.calibrationComponentKey],
        anchors,
      });
      return true;
    }

    redrawHotspots() {
      this.labels.forEach(({ anchor, el }) => {
        if (anchor?.parent) anchor.parent.remove(anchor);
        el?.remove();
      });
      this.labels = [];
      const removable = [];
      this.group?.traverse((object) => {
        if (object.userData?.hotspotMarker) removable.push(object);
      });
      removable.forEach((object) => object.parent?.remove(object));
      this.addComponentHotspots(this.currentModel);
      this.updateLabels();
    }

    addSemanticEquipmentOverlay(model) {
      const equipment = model?.equipment || (model?.id || "").replace(/^std-/, "").split("-")[0];
      if (equipment === "bearing") {
        this.torus("outer_ring", 0.92, 0.055, [0, 0, 0.02], this.overlayColor("outer_ring"), 0.32);
        this.torus("inner_ring", 0.48, 0.045, [0, 0, 0.08], this.overlayColor("inner_ring"), 0.3);
        this.torus("seal_pair", 0.69, 0.025, [0, 0, 0.22], this.overlayColor("seal_pair"), 0.28);
        this.torus("cage", 0.62, 0.02, [0, 0, -0.1], this.overlayColor("cage"), 0.22);
        for (let i = 0; i < 12; i += 1) {
          const angle = (Math.PI * 2 * i) / 12;
          this.sphere("rolling_elements", 0.07, [Math.cos(angle) * 0.62, Math.sin(angle) * 0.62, 0.02], this.overlayColor("rolling_elements"), 0.38);
        }
      } else if (equipment === "motor") {
        this.cylinder("motor_housing", 0.52, 0.52, 1.72, [0, 0, 0], [0, 0, Math.PI / 2], COLORS.dark, 0.3);
        this.cylinder("front_bearing_end", 0.36, 0.36, 0.16, [-1.02, 0, 0], [0, 0, Math.PI / 2], this.overlayColor("front_bearing_end"), 0.62);
        this.cylinder("output_shaft", 0.075, 0.075, 2.28, [0, 0, 0], [0, 0, Math.PI / 2], COLORS.amber, 0.7);
        this.box("end_cover", [0.2, 1.16, 1.16], [-1.22, 0, 0], this.overlayColor("end_cover"), 0.52);
        this.box("terminal_connector", [0.48, 0.22, 0.34], [-0.38, 0.68, 0.24], this.overlayColor("terminal_connector"), 0.62);
        this.box("mounting_flange", [0.16, 1.34, 1.34], [-1.42, 0, 0], this.overlayColor("mounting_flange"), 0.3);
      } else if (equipment === "pump") {
        this.cylinder("motor_body", 0.36, 0.36, 0.92, [-0.82, 0, 0], [0, 0, Math.PI / 2], COLORS.steel, 0.28);
        this.cylinder("pump_casing", 0.48, 0.48, 0.28, [0.34, 0, 0], [Math.PI / 2, 0, 0], COLORS.dark, 0.3);
        this.cylinder("pump_head", 0.33, 0.33, 0.24, [0.52, 0, 0.02], [Math.PI / 2, 0, 0], this.overlayColor("pump_head"), 0.42);
        this.cylinder("pump_seal_zone", 0.18, 0.18, 0.18, [-0.22, 0, 0.02], [0, 0, Math.PI / 2], this.overlayColor("pump_seal_zone"), 0.66);
        this.cylinder("impeller", 0.26, 0.26, 0.12, [0.35, 0, 0.08], [Math.PI / 2, 0, 0], COLORS.blue, 0.54);
        this.cylinder("pump_shaft", 0.06, 0.06, 1.55, [-0.2, 0, 0.02], [0, 0, Math.PI / 2], COLORS.amber, 0.7);
        this.cylinder("inlet_outlet", 0.12, 0.12, 0.68, [0.84, 0.48, 0.2], [0, 0, 0], this.overlayColor("inlet_outlet"), 0.62);
        this.cylinder("inlet_outlet", 0.12, 0.12, 0.58, [0.84, -0.48, 0.2], [0, 0, 0], this.overlayColor("inlet_outlet"), 0.5);
        this.box("mounting_bracket", [1.42, 0.14, 0.18], [-0.08, -0.58, -0.28], this.overlayColor("mounting_bracket"), 0.5);
      } else if (equipment === "engine") {
        this.box("crankcase", [1.25, 0.55, 0.88], [-0.1, -0.42, 0], COLORS.dark, 0.3);
        this.box("cylinder_block", [1.05, 0.68, 0.82], [-0.18, 0.06, 0], COLORS.dark, 0.3);
        this.box("cylinder_head", [1.0, 0.32, 0.84], [-0.18, 0.58, 0.04], COLORS.steel, 0.5);
        [-0.04, 0.08, 0.2, 0.32].forEach((y) => {
          this.box("cooling_fins", [1.14, 0.035, 0.9], [-0.18, y, 0.02], this.overlayColor("cooling_fins"), 0.46);
        });
        this.box("spark_plug", [0.18, 0.55, 0.18], [0.28, 0.88, 0.16], this.overlayColor("spark_plug"), 0.78);
        this.box("intake_exhaust_ports", [0.42, 0.28, 0.36], [0.72, 0.18, 0.08], this.overlayColor("intake_exhaust_ports"), 0.58);
        this.box("wiring_harness", [0.14, 0.72, 0.14], [-0.76, 0.26, 0.12], this.overlayColor("wiring_harness"), 0.58);
        this.box("starter_motor", [0.74, 0.28, 0.28], [-0.92, -0.36, 0.1], COLORS.blue, 0.58);
        this.cylinder("water_pump", 0.2, 0.2, 0.18, [0.96, -0.22, 0.08], [Math.PI / 2, 0, 0], this.overlayColor("water_pump"), 0.66);
      }
    }

    overlayColor(key) {
      return this.isHighlighted(key) ? this.toneColor(this.componentTone(key)) : COLORS.blue;
    }

    torus(key, radius, tube, position, color, opacity) {
      const mesh = new THREE.Mesh(
        new THREE.TorusGeometry(radius, tube, 18, 112),
        this.material(color, { transparent: true, opacity, metalness: 0.08, roughness: 0.36, depthWrite: false }),
      );
      mesh.position.set(position[0], position[1], position[2]);
      mesh.userData = { componentKey: key, basePosition: mesh.position.clone(), semanticOverlay: true };
      this.group.add(mesh);
      if (key && !this.meshes.has(key)) this.meshes.set(key, mesh);
      return mesh;
    }

    sphere(key, radius, position, color, opacity) {
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(radius, 28, 14),
        this.material(color, { transparent: true, opacity, metalness: 0.16, roughness: 0.26, depthWrite: false }),
      );
      mesh.position.set(position[0], position[1], position[2]);
      mesh.userData = { componentKey: key, basePosition: mesh.position.clone(), semanticOverlay: true };
      this.group.add(mesh);
      if (key && !this.meshes.has(key)) this.meshes.set(key, mesh);
      return mesh;
    }

    cylinder(key, radiusTop, radiusBottom, height, position, rotation = [0, 0, 0], color, opacity = 0.45) {
      const mesh = new THREE.Mesh(
        new THREE.CylinderGeometry(radiusTop, radiusBottom, height, 36, 1, false),
        this.material(color, { transparent: true, opacity, metalness: 0.14, roughness: 0.38, depthWrite: false }),
      );
      mesh.position.set(position[0], position[1], position[2]);
      mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
      mesh.userData = { componentKey: key, basePosition: mesh.position.clone(), semanticOverlay: true };
      this.group.add(mesh);
      if (key && !this.meshes.has(key)) this.meshes.set(key, mesh);
      return mesh;
    }

    box(key, size, position, color, opacity = 0.45) {
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(size[0], size[1], size[2]),
        this.material(color, { transparent: true, opacity, metalness: 0.12, roughness: 0.48 }),
      );
      mesh.position.set(position[0], position[1], position[2]);
      mesh.userData = { componentKey: key, basePosition: mesh.position.clone(), semanticOverlay: true };
      this.group.add(mesh);
      if (key) this.meshes.set(key, mesh);
      return mesh;
    }

    addComponentHotspots(model) {
      this.visibleHotspotComponents(model).forEach((component) => {
        const position = this.componentAnchorPosition(component);
        const tone = this.componentTone(component.component_key);
        const marker = new THREE.Mesh(
          new THREE.SphereGeometry(this.isHighlighted(component.component_key) ? 0.055 : 0.038, 24, 12),
          this.material(this.toneColor(tone), { transparent: true, opacity: this.isHighlighted(component.component_key) ? 0.94 : 0.54, emissive: this.toneColor(tone), emissiveIntensity: 0.12 }),
        );
        marker.position.set(position[0], position[1], position[2]);
        marker.userData = { componentKey: component.component_key, basePosition: marker.position.clone(), hotspotMarker: true };
        this.group.add(marker);
        this.addLabel(component.component_key, component.label, position, this.highlightSubtitle(component.component_key));
      });
    }

    visibleHotspotComponents(model) {
      const components = model.components || [];
      const highlightedKeys = Object.keys(this.highlightByKey);
      const equipment = model?.equipment || this.currentModel?.equipment || "";
      if (highlightedKeys.length) {
        const highlighted = components.filter((component) => highlightedKeys.includes(component.component_key));
        if (highlighted.length) return highlighted;
      }
      const keys = DEFAULT_VISIBLE_COMPONENT_KEYS[equipment] || [];
      const preferred = Array.isArray(keys) && keys.length
        ? components.filter((component) => keys.includes(component.component_key))
        : components;
      const calibrated = components.filter((component) => this.hasCalibratedAnchor(component.component_key));
      const merged = [...calibrated, ...(preferred.length ? preferred : components.slice(0, 4))];
      const seen = new Set();
      return merged.filter((component) => {
        if (!component?.component_key || seen.has(component.component_key)) return false;
        seen.add(component.component_key);
        return true;
      });
    }

    componentAnchorPosition(component) {
      const key = component?.component_key || "";
      const calibratedAnchor = this.calibratedAnchors.get(key);
      if (calibratedAnchor && [calibratedAnchor.x, calibratedAnchor.y, calibratedAnchor.z].every(Number.isFinite)) {
        return [calibratedAnchor.x, calibratedAnchor.y, calibratedAnchor.z];
      }
      if (this.prefersCuratedAnchor(component)) return [...COMPONENT_LABEL_ANCHORS[key]];
      const sidecarHotspot = this.sidecarHotspotPosition(component);
      if (sidecarHotspot) return sidecarHotspot;
      const sourceNode = component?.geometry?.source_node || "";
      const sourceKey = this.markerComponentKey(sourceNode);
      const markerAnchor = this.namedMarkerAnchors.get(sourceKey || key) || this.namedMarkerAnchors.get(key);
      if (markerAnchor && [markerAnchor.x, markerAnchor.y, markerAnchor.z].every(Number.isFinite)) {
        return [markerAnchor.x, markerAnchor.y, markerAnchor.z];
      }
      const mesh = this.meshes.get(key);
      const anchor = mesh?.userData?.labelAnchorPosition || mesh?.userData?.basePosition || mesh?.position;
      if (anchor && [anchor.x, anchor.y, anchor.z].every(Number.isFinite)) return [anchor.x, anchor.y, anchor.z];
      if (COMPONENT_LABEL_ANCHORS[key]) return [...COMPONENT_LABEL_ANCHORS[key]];
      return [0, 0.8, 0.2];
    }

    prefersCuratedAnchor(component) {
      const key = component?.component_key || "";
      return this.currentModel?.equipment === "engine" && Boolean(COMPONENT_LABEL_ANCHORS[key]);
    }

    sidecarHotspotPosition(component) {
      const hotspot = component?.hotspot || {};
      const hasAnyCoordinate = Number.isFinite(hotspot.x) || Number.isFinite(hotspot.y) || Number.isFinite(hotspot.z);
      if (!hasAnyCoordinate) return null;
      return [
        Number.isFinite(hotspot.x) ? hotspot.x : 0,
        Number.isFinite(hotspot.y) ? hotspot.y : 0.8,
        Number.isFinite(hotspot.z) ? hotspot.z : 0.2,
      ];
    }

    addLabel(componentKey, label, position, subtitle = "") {
      if (!this.labelLayer) return;
      const meta = this.highlightByKey[componentKey] || {};
      const anchorKind = this.anchorClass(componentKey);
      const anchor = new THREE.Object3D();
      anchor.position.set(position[0], position[1], position[2]);
      anchor.userData = { componentKey, basePosition: anchor.position.clone(), labelAnchor: true };
      this.group.add(anchor);
      const el = document.createElement("div");
      const isExpanded = this.expandedLabelKey === componentKey;
      el.className = `spatial-hotspot-label tone-${meta.tone || "info"} anchor-${anchorKind}${this.isHighlighted(componentKey) ? " active" : ""}${isExpanded ? " expanded" : ""}`;
      el.dataset.componentKey = componentKey;
      el.setAttribute("role", "button");
      el.setAttribute("tabindex", "0");
      el.setAttribute("aria-pressed", isExpanded ? "true" : "false");
      el.setAttribute("title", "点击查看标注详情");
      el.innerHTML = `<strong>${this.escapeHtml(label)}</strong>${subtitle ? `<span>${this.escapeHtml(subtitle)}</span>` : ""}`;
      const openDetail = (event) => {
        event.preventDefault();
        event.stopPropagation();
        this.focusComponent(componentKey);
      };
      el.addEventListener("click", openDetail);
      el.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") openDetail(event);
      });
      this.labelLayer.appendChild(el);
      this.labels.push({ anchor, el, componentKey });
    }

    anchorClass(componentKey) {
      if (this.hasCalibratedAnchor(componentKey)) return "calibrated";
      const component = (this.currentModel?.components || []).find((item) => item.component_key === componentKey);
      if (this.prefersCuratedAnchor(component)) return "auto";
      if (this.namedMarkerAnchors.has(componentKey)) return "model";
      return "auto";
    }

    anchorSource(componentKey) {
      if (this.hasCalibratedAnchor(componentKey)) return "人工校准锚点";
      const component = (this.currentModel?.components || []).find((item) => item.component_key === componentKey);
      if (this.prefersCuratedAnchor(component)) return "系统预标";
      if (this.sidecarHotspotPosition(component)) return "辅助标注预标";
      if (this.namedMarkerAnchors.has(componentKey)) return "模型内置预标";
      if (COMPONENT_LABEL_ANCHORS[componentKey]) return "系统预标";
      return "辅助标注预标";
    }

    highlightSubtitle(componentKey) {
      const meta = this.highlightByKey[componentKey];
      const source = this.anchorSource(componentKey);
      if (!meta) return source;
      const confidence = Math.round((meta.confidence || 0) * 100);
      return `${confidence}% · ${source} · ${meta.reason || "证据命中"}`;
    }

    showProcedural(model) {
      const equipment = model?.equipment || (model?.id || "").replace(/^std-/, "").split("-")[0];
      if (["bearing", "pump", "motor", "engine"].includes(equipment)) {
        this.addSemanticEquipmentOverlay({ equipment });
        this.addComponentHotspots(model);
      } else {
        this.box("default", [1.4, 1.0, 1.0], [0, 0, 0], COLORS.dark, 0.36);
        this.addComponentHotspots(model);
      }
      this.group.rotation.set(-0.12, -0.62, 0);
      this.applySection();
      this.fitToContents();
      this.updateLabels();
    }

    applyCameraDistance(distance) {
      if (!this.camera || !this.cameraTarget) return;
      const direction = this.camera.position.clone().sub(this.cameraTarget);
      if (direction.lengthSq() < 0.001) direction.set(3.8, 2.65, 5.2);
      direction.normalize();
      this.camera.position.copy(this.cameraTarget).add(direction.multiplyScalar(distance));
      this.camera.lookAt(this.cameraTarget);
    }

    fitToContents() {
      if (!this.group || !this.camera || !this.cameraTarget) return;
      this.group.updateMatrixWorld(true);
      const box = this.sceneContentBox();
      if (box.isEmpty()) return;
      const size = new THREE.Vector3();
      const center = new THREE.Vector3();
      box.getSize(size);
      box.getCenter(center);
      if (![size.x, size.y, size.z, center.x, center.y, center.z].every(Number.isFinite)) return;
      const maxDim = Math.max(size.x, size.y, size.z, 1);
      const fov = THREE.MathUtils.degToRad(this.camera.fov);
      const aspect = Math.max(this.camera.aspect || 1, 0.1);
      const fitHeightDistance = maxDim / (2 * Math.tan(fov / 2));
      const fitWidthDistance = fitHeightDistance / aspect;
      const padding = this.currentModel?.equipment === "pump" ? 0.98 : 1.18;
      const distance = Math.max(fitHeightDistance, fitWidthDistance) * padding;
      const direction = new THREE.Vector3(3.4, 2.25, 4.4).normalize();
      this.cameraTarget.copy(center);
      this.zoom = Math.max(2.9, Math.min(6.6, distance));
      this.camera.position.copy(center).add(direction.multiplyScalar(this.zoom));
      this.camera.lookAt(center);
      this.camera.updateProjectionMatrix();
    }

    sceneContentBox() {
      const preferredBox = new THREE.Box3();
      const fallbackBox = new THREE.Box3();
      let hasPreferred = false;
      let hasFallback = false;
      this.group.updateMatrixWorld(true);
      this.group.traverse((node) => {
        if (!node.isMesh || node.visible === false) return;
        if (node.userData?.hotspotMarker || node.userData?.labelAnchor || node.userData?.sectionPlane) return;
        if (node.userData?.baseModelMesh) {
          preferredBox.expandByObject(node);
          hasPreferred = true;
          return;
        }
        if (node.userData?.semanticOverlay || node.userData?.componentKey) {
          fallbackBox.expandByObject(node);
          hasFallback = true;
        }
      });
      if (hasPreferred) return preferredBox;
      if (hasFallback) return fallbackBox;
      return new THREE.Box3().setFromObject(this.group);
    }

    resetView() {
      this.zoom = 5.2;
      if (this.group) this.group.rotation.set(-0.12, -0.62, 0);
      if (this.group?.children.length) {
        this.fitToContents();
      } else {
        this.cameraTarget?.set(0, VIEWPORT_GROUP_OFFSET_Y, 0);
        this.camera.position.set(3.8, 2.65, this.zoom);
        this.camera.lookAt(this.cameraTarget || new THREE.Vector3(0, 0, 0));
      }
      this.updateLabels();
    }

    setSection(enabled) {
      const equipment = this.currentModel?.equipment || "";
      this.sectionEnabled = Boolean(enabled && SECTION_SUPPORTED_EQUIPMENT.has(equipment));
      this.applySection();
    }

    applySection() {
      if (!this.group) return;
      if (this.sectionPlaneMesh) {
        this.group.remove(this.sectionPlaneMesh);
        this.sectionPlaneMesh = null;
      }
      const sectionCenter = new THREE.Vector3(0, VIEWPORT_GROUP_OFFSET_Y, 0);
      const sectionSize = new THREE.Vector3(2.55, 2.55, 2.55);
      if (this.sectionEnabled) {
        const box = this.sceneContentBox();
        if (!box.isEmpty()) {
          box.getCenter(sectionCenter);
          box.getSize(sectionSize);
        }
      }
      this.clipPlane = this.sectionEnabled ? new THREE.Plane(new THREE.Vector3(-1, 0, 0), sectionCenter.x) : null;
      this.group.traverse((node) => {
        if (!node.isMesh) return;
        const materials = Array.isArray(node.material) ? node.material : [node.material];
        materials.filter(Boolean).forEach((material) => {
          material.clippingPlanes = this.clipPlane ? [this.clipPlane] : [];
          material.needsUpdate = true;
        });
      });
      if (this.sectionEnabled) {
        const planeHeight = Math.max(sectionSize.y * 1.18, 1.6);
        const planeDepth = Math.max(sectionSize.z * 1.18, 1.6);
        const plane = new THREE.Mesh(
          new THREE.BoxGeometry(0.018, planeHeight, planeDepth),
          this.material(COLORS.section, { transparent: true, opacity: 0.16, side: THREE.DoubleSide, depthWrite: false }),
        );
        plane.position.set(sectionCenter.x, sectionCenter.y, sectionCenter.z);
        plane.userData = { sectionPlane: true };
        this.group.add(plane);
        this.sectionPlaneMesh = plane;
      }
    }

    focusComponent(componentKey) {
      this.focusedComponentKey = componentKey || "";
      this.expandedLabelKey = componentKey || "";
      const rotations = {
        outer_ring: [-0.12, -0.5, 0],
        rolling_elements: [-0.1, -0.3, 0],
        inner_ring: [-0.1, -0.2, 0],
        cage: [-0.12, 0.15, 0],
        seal_pair: [-0.2, 0.5, 0],
        seal_lubrication: [-0.2, 0.5, 0],
        mechanical_seal: [-0.15, 0.3, 0],
        pump_seal_zone: [-0.15, 0.3, 0],
        pump_head: [-0.15, 0.2, 0],
        impeller: [-0.12, 0.0, 0],
        pump_shaft: [-0.1, 0.0, 0],
        pump_casing: [-0.18, -0.25, 0],
        motor_body: [-0.15, -0.4, 0],
        inlet_outlet: [-0.18, 0.4, 0],
        mounting_bracket: [-0.2, -0.2, 0],
        front_bearing: [-0.1, 0.2, 0],
        front_bearing_end: [-0.1, 0.2, 0],
        end_cover: [-0.1, 0.3, 0],
        output_shaft: [-0.08, 0.1, 0],
        rotor_shaft: [-0.08, 0.1, 0],
        motor_housing: [-0.15, 0.0, 0],
        terminal_connector: [-0.2, -0.5, 0],
        mounting_flange: [-0.15, 0.3, 0],
        stator_winding: [-0.15, 0.0, 0],
        spark_plug: [-0.25, 0.1, 0],
        cylinder: [-0.2, 0.0, 0],
        cylinder_head: [-0.2, 0.0, 0],
        cylinder_block: [-0.18, 0.0, 0],
        crankcase: [-0.15, 0.0, 0],
        cooling_fins: [-0.25, -0.3, 0],
        intake_exhaust_ports: [-0.2, 0.4, 0],
        wiring_harness: [-0.15, -0.5, 0],
        starter_motor: [-0.15, -0.5, 0],
        water_pump: [-0.2, 0.4, 0],
      };
      if (this.group && rotations[componentKey]) {
        this.group.rotation.set(rotations[componentKey][0], rotations[componentKey][1], rotations[componentKey][2]);
      }
      this.labels.forEach(({ el, componentKey: key }) => {
        const selected = Boolean(componentKey && key === componentKey);
        el.classList.toggle("focused", selected);
        el.classList.toggle("expanded", selected);
        el.setAttribute("aria-pressed", selected ? "true" : "false");
      });
      this.updateLabels();
    }

    resize() {
      if (!this.renderer || !this.camera) return;
      const width = Math.max(320, this.container.clientWidth || 640);
      const height = Math.max(260, this.container.clientHeight || 420);
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height, false);
      this.updateLabels();
    }

    updateLabels() {
      if (!this.camera || !this.renderer || !this.labelLayer) return;
      const rect = this.container.getBoundingClientRect();
      const vector = new THREE.Vector3();
      const projected = this.labels.map(({ anchor, el }) => {
        vector.setFromMatrixPosition(anchor.matrixWorld);
        vector.project(this.camera);
        const visible = vector.z > -1 && vector.z < 1;
        const x = (vector.x * 0.5 + 0.5) * rect.width;
        const y = (-vector.y * 0.5 + 0.5) * rect.height;
        return {
          el,
          visible,
          x,
          y,
          width: el.offsetWidth || 160,
          height: el.offsetHeight || 52,
        };
      });
      const placedLabels = [];
      projected.sort((a, b) => a.y - b.y).forEach((item) => {
        const { el, visible, x, y, width, height } = item;
        let left = Math.max(6, Math.min(rect.width - width - 6, x + 3));
        let top = Math.max(6, Math.min(rect.height - height - 6, y - 20));
        let attempts = 0;
        while (placedLabels.some((placed) => Math.abs(placed.left - left) < Math.max(width, placed.width) + 12 && Math.abs(placed.top - top) < Math.max(height, placed.height) + 8) && attempts < 10) {
          top += height + 8;
          if (top > rect.height - height - 6) {
            top = 6 + attempts * 8;
            left = Math.min(rect.width - width - 6, left + 28);
          }
          attempts += 1;
        }
        el.dataset.detailPlacement = left + 236 > rect.width - 6 ? "right" : "left";
        el.dataset.detailVertical = top + height + 104 > rect.height - 6 ? "top" : "bottom";
        el.style.transform = `translate(${left}px, ${top}px)`;
        el.style.opacity = visible ? "1" : "0";
        if (visible) placedLabels.push({ left, top, width, height });
      });
    }

    animate() {
      if (!this.renderer || !this.scene || !this.camera) return;
      this.raf = requestAnimationFrame(() => this.animate());
      this.renderer.render(this.scene, this.camera);
      this.updateLabels();
    }

    dispose() {
      cancelAnimationFrame(this.raf);
      if (this.resizeObserver) this.resizeObserver.disconnect();
      if (this.renderer) this.renderer.dispose();
    }
  }

  window.A1ThreeWorkbench = A1ThreeWorkbench;
})();
