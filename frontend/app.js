const { createApp, nextTick } = Vue;

createApp({
  data() {
    return {
      activeTab: "diagnosis",
      tabs: [
        { id: "diagnosis", label: "问诊检修", icon: "stethoscope" },
        { id: "cases", label: "案例审核", icon: "clipboard-check" },
        { id: "graph", label: "知识图谱", icon: "network" },
        { id: "metrics", label: "评测面板", icon: "bar-chart-3" },
        { id: "resources", label: "资源与模型", icon: "folder-cog" },
      ],
      health: {},
      providers: [],
      agentRoutes: [],
      devices: [],
      levels: [],
      loading: false,
      query: {
        equipment: "motor",
        model: "Y2-160M",
        maintenance_level: "二级检修",
        text: "电机运行 30 分钟后端盖温度升高，伴随低频振动和轴承异响",
        image_caption: "",
        top_k: 6,
      },
      uploadedImage: {},
      result: null,
      pendingCases: [],
      feedbackRecords: [],
      graph: { nodes: [], edges: [] },
      metrics: { benchmarks: [] },
      reviewStatus: { cases: {}, eval_questions: {}, targets: {} },
      modelResults: [],
      adminResult: "等待操作",
      caseForm: {
        title: "现场新增：轴承座油污和温升",
        equipment: "motor",
        model: "Y2-160M",
        symptoms: "端盖附近油污增加，运行后温度上升，振动值高于基线。",
        fault_type: "过热/油污",
        cause: "疑似密封老化和润滑脂污染，需要拆检确认。",
        actions: "停机断电挂牌，拆检端盖和轴承，清理轴承室，更换密封圈并补充润滑脂。",
        parts: "密封圈, 润滑脂, 6205 轴承",
        risk_level: "medium",
      },
      feedbackForm: {
        corrected_answer: "",
        notes: "",
      },
      feedbackStatus: "",
    };
  },
  computed: {
    currentTitle() {
      return this.tabs.find((tab) => tab.id === this.activeTab)?.label || "工作台";
    },
    graphLayout() {
      const nodes = this.graph.nodes || [];
      const edges = this.graph.edges || [];
      const centerX = 480;
      const centerY = 250;
      const radius = 190;
      const positioned = nodes.map((node, index) => {
        const angle = (Math.PI * 2 * index) / Math.max(1, nodes.length);
        return {
          ...node,
          x: centerX + Math.cos(angle) * radius,
          y: centerY + Math.sin(angle) * radius,
          r: node.type === "equipment" ? 26 : 18,
        };
      });
      const byId = Object.fromEntries(positioned.map((node) => [node.id, node]));
      return {
        nodes: positioned,
        edges: edges
          .map((edge) => {
            const source = byId[edge.source];
            const target = byId[edge.target];
            if (!source || !target) return null;
            return { ...edge, x1: source.x, y1: source.y, x2: target.x, y2: target.y };
          })
          .filter(Boolean),
      };
    },
  },
  async mounted() {
    await this.refreshAll();
  },
  updated() {
    this.paintIcons();
  },
  methods: {
    paintIcons() {
      nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    },
    async api(path, options = {}) {
      const apiBase = (window.A1_API_BASE_URL || "").replace(/\/$/, "");
      const res = await fetch(`${apiBase}${path}`, options);
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    async refreshAll() {
      const [health, devices, providers, routes, graph, metrics, reviewStatus, pending, feedback] = await Promise.all([
        this.api("/api/health"),
        this.api("/api/devices"),
        this.api("/api/providers"),
        this.api("/api/agent-routing"),
        this.api("/api/knowledge-graph"),
        this.api("/api/metrics"),
        this.api("/api/review-status"),
        this.api("/api/cases?status=pending"),
        this.api("/api/feedback"),
      ]);
      this.health = health;
      this.devices = devices.devices;
      this.levels = devices.levels;
      this.providers = providers.providers;
      this.agentRoutes = routes.routes;
      this.graph = graph;
      this.metrics = metrics;
      this.reviewStatus = reviewStatus;
      this.pendingCases = pending.cases;
      this.feedbackRecords = feedback.feedback;
      this.paintIcons();
    },
    async uploadImage(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      const form = new FormData();
      form.append("file", file);
      this.uploadedImage = await this.api("/api/upload-image", { method: "POST", body: form });
      this.query.image_caption = this.uploadedImage.caption;
      this.paintIcons();
    },
    async runQuery() {
      this.loading = true;
      try {
        this.result = await this.api("/api/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.query),
        });
        this.prepareFeedbackDraft();
      } finally {
        this.loading = false;
        this.paintIcons();
      }
    },
    composeOriginalAnswer() {
      if (!this.result) return "";
      return [
        `故障判断：${this.result.diagnosis}`,
        `可能原因：${(this.result.possible_causes || []).join("；")}`,
        `作业步骤：${(this.result.sop_steps || []).join("；")}`,
        `模型复核：${this.result.model_review?.text || ""}`,
      ].join("\n");
    },
    prepareFeedbackDraft() {
      this.feedbackForm.corrected_answer = this.composeOriginalAnswer();
      this.feedbackForm.notes = "";
      this.feedbackStatus = "";
    },
    async submitFeedback() {
      if (!this.result) return;
      const payload = {
        question: this.result.query,
        original_answer: this.composeOriginalAnswer(),
        corrected_answer: this.feedbackForm.corrected_answer,
        notes: this.feedbackForm.notes,
      };
      await this.api("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      this.feedbackStatus = "已记录人工修正";
      await this.refreshAll();
    },
    async submitCase() {
      await this.api("/api/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.caseForm),
      });
      await this.refreshAll();
    },
    async approveCase(id) {
      await this.api(`/api/cases/${id}/approve`, { method: "POST" });
      await this.refreshAll();
    },
    async ingestManuals() {
      const result = await this.api("/api/admin/ingest-manuals", { method: "POST" });
      this.adminResult = JSON.stringify(result, null, 2);
      await this.refreshAll();
    },
    async rebuildIndex() {
      const result = await this.api("/api/admin/rebuild-index", { method: "POST" });
      this.adminResult = JSON.stringify(result, null, 2);
      await this.refreshAll();
    },
    async generateSampleData() {
      const result = await this.api("/api/admin/generate-sample-data", { method: "POST" });
      this.adminResult = JSON.stringify(result, null, 2);
      await this.refreshAll();
    },
    async runEval(maxQuestions = 20) {
      const suffix = maxQuestions ? `?max_questions=${maxQuestions}` : "";
      const result = await this.api(`/api/eval/run${suffix}`, { method: "POST" });
      this.adminResult = JSON.stringify(result, null, 2);
      await this.refreshAll();
    },
    async discoverModels() {
      const result = await this.api("/api/models");
      this.modelResults = result.results;
      this.adminResult = JSON.stringify(result, null, 2);
      this.paintIcons();
    },
    riskLabel(level) {
      return { high: "高", medium: "中", low: "低" }[level] || level;
    },
  },
}).mount("#app");
