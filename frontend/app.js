const { createApp, nextTick } = Vue;

const GRAPH_DISPLAY_LIMIT = 40;
const GRAPH_EDGE_LIMIT = 58;
const GRAPH_TYPE_LIMIT = {
  Equipment: 1,
  Component: 8,
  Fault: 10,
  VisualAsset: 4,
  SafetyRule: 8,
  Case: 5,
  ManualChunk: 6,
  Process: 2,
};
const GRAPH_TYPE_WEIGHT = {
  Equipment: 100,
  Component: 85,
  Fault: 80,
  VisualAsset: 72,
  SafetyRule: 64,
  Case: 48,
  ManualChunk: 42,
  Process: 36,
};
const EQUIPMENT_QUERY_PRESETS = {
  motor: {
    model: "Y2-160M",
    maintenance_level: "二级检修",
    text: "电机运行 30 分钟后端盖温度升高，伴随低频振动和轴承异响。请给出故障判断、拆检前安全确认、SOP 和验收标准。",
  },
  pump: {
    model: "ISG80-160",
    maintenance_level: "三级检修",
    text: "离心泵机械密封持续滴漏，现场人员想直接拆卸端盖，请判断现在能不能修、应该按什么流程处理。",
  },
  bearing: {
    model: "6201-2RS",
    maintenance_level: "二级检修",
    text: "轴承运行时出现周期性冲击声，手动转动有颗粒感。请判断滚道、外圈或滚动体是否存在剥落，并生成拆检步骤。",
  },
  engine: {
    model: "motorcycle-engine-hd",
    maintenance_level: "二级检修",
    text: "发动机冷车起动困难，火花塞有积碳，怀疑间隙异常。请依据维修手册给出火花塞检查、压缩压力复核和复装注意事项。",
  },
};

createApp({
  data() {
    return {
      activeTab: "overview",
      navGroups: [
        { id: "overview", label: "总览", icon: "layout-dashboard", children: [] },
        { id: "diagnosis", label: "检修任务", icon: "stethoscope", children: [
          { id: "diagnosis", label: "检修任务台" },
          { id: "diagnosis_vision", label: "图片识别详情" },
        ]},
        { id: "claim", label: "检修判断卡", icon: "file-badge-2", children: [
          { id: "claim_list", label: "判断卡列表" },
          { id: "claim_detail", label: "判断卡复核" },
        ]},
        { id: "evidence", label: "证据工作台", icon: "book-open-check", children: [] },
        { id: "graph", label: "证据链图谱", icon: "network", children: [] },
        { id: "spatial", label: "CAD结构工位", icon: "cuboid", children: [
          { id: "spatial", label: "结构主页" },
          { id: "spatial_calibration", label: "锚点校准" },
          { id: "spatial_asset", label: "资产详情" },
        ]},
        { id: "safety", label: "作业票与安全", icon: "shield-alert", children: [
          { id: "safety_list", label: "作业票列表" },
          { id: "safety", label: "安全执行" },
        ]},
        { id: "cases", label: "知识沉淀", icon: "clipboard-check", children: [
          { id: "cases", label: "案例草稿与上传" },
          { id: "cases_review", label: "案例审核看板" },
          { id: "cases_write", label: "知识写入/回滚" },
        ]},
        { id: "metrics", label: "评测证明", icon: "bar-chart-3", children: [
          { id: "metrics", label: "评测总览" },
          { id: "metrics_failure", label: "失败分析" },
        ]},
        { id: "resources", label: "资源管理", icon: "folder-cog", children: [
          { id: "resources", label: "资源总览" },
          { id: "resources_ops", label: "操作中心" },
          { id: "resources_models", label: "系统架构" },
        ]},
      ],
      expandedNavGroup: "",
      health: {},
      providers: [],
      agentRoutes: [],
      devices: [],
      levels: [],
      loading: false,
      agentProgressIndex: 0,
      agentProgressTimer: null,
      queryError: "",
      query: {
        equipment: "",
        model: "",
        maintenance_level: "二级检修",
        text: "",
        image_caption: "",
        visual_asset_id: null,
        top_k: 6,
      },
      uploadedImage: {},
      uploadingImage: false,
      uploadStatus: "",
      result: null,
      currentSession: {
        task_id: "draft",
        equipment: "",
        model: "",
        query_text: "",
        visual_asset_id: null,
        selected_component_keys: [],
        selected_model_component_keys: [],
        tri_mro_alignment: null,
        claim_cards: [],
        primary_claim_card: null,
        workflow_state: {
          task_id: "draft",
          equipment: "",
          model: "",
          selected_component_keys: [],
          selected_model_component_keys: [],
          stages: [],
          safety_gate: { status: "unknown", label: "等待生成方案", blocking_items: [] },
        },
        visual_analysis: null,
        updated_at: "",
      },
      pendingCases: [],
      feedbackRecords: [],
      graph: { nodes: [], edges: [] },
      graphStatus: {},
      graphFocus: "motor",
      graphLayers: {
        Component: true,
        Fault: true,
        Cause: true,
        Process: true,
        SafetyRule: true,
        Case: true,
        ManualChunk: true,
        VisualAsset: true,
      },
      selectedGraphNodeId: "",
      visualAssets: [],
      activeExplanation: "",
      selectedClaimReviewPanel: "evidence",
      activeEvidenceGroup: "manual",
      selectedVisualAssetId: "",
      metrics: { benchmarks: [] },
      reviewStatus: { cases: {}, eval_questions: {}, targets: {} },
      imageEvalStatus: { by_equipment: {}, missing_paths: [] },
      resourceVerification: { summary: {}, resources: [] },
      partTreeCandidates: { summary: {}, candidates: [], blocked_sources: [], next_steps: [] },
      partTreeEquipment: "all",
      candidateCadAssets: [],
      candidateCadSummary: {},
      cadRuntime: { tools: {}, recommended_mode: "unknown" },
      selectedCandidateCadId: "",
      candidateCadSpecDraft: "",
      candidateCadReviewStatus: "选择候选资产后可编辑 CAD spec、重新渲染并晋升为结构链资产。",
      candidateCadStatus: "等待从现场照片生成候选 CAD",
      latestKnowledgeWrite: null,
      candidateCadLightbox: {
        open: false,
        assetId: "",
        view: "iso",
        rotation: 0,
        mode: "glb",
      },
      candidateCadGlbViewer: null,
      candidateCadGlbViewerToken: "",
      modelResults: [],
      spatialModels: [],
      selectedSpatialModelId: "",
      selectedSpatialModel: { components: [] },
      spatialGuidance: null,
      spatialViewer: null,
      spatialModelSource: "local",
      photoCadGeneration: {
        status: "idle",
        visual_asset_id: null,
        candidate_id: "",
        message: "上传故障照片后，系统会自动生成照片 CAD 候选资产。",
        error: "",
      },
      lastTaskTab: "diagnosis",
      spatialSection: false,
      focusedSpatialComponentKey: "",
      spatialCalibrationMode: false,
      spatialCalibrationComponentKey: "",
      reconstructionJobs: [],
      multiPhotoFiles: [],
      activeResourcePage: "comparison",
      resourceOperationStatus: "选择一个资源页面查看说明、运行状态和结果。",
      adminResult: "等待操作",
      resourceOperationResult: null,
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
      safetyConfirmations: {},
      feedbackForm: {
        corrected_answer: "",
        notes: "",
      },
      feedbackStatus: "",
    };
  },
  computed: {
    tabs() {
      const flat = [];
      this.navGroups.forEach((g) => {
        if (!g.children.length) flat.push({ id: g.id, label: g.label, icon: g.icon });
        else g.children.forEach((c) => flat.push({ id: c.id, label: c.label, icon: g.icon }));
      });
      return flat;
    },
    allNavIds() {
      return this.tabs.map((t) => t.id);
    },
    activeNavGroup() {
      for (const g of this.navGroups) {
        if (g.id === this.activeTab) return g.id;
        if (g.children.some((c) => c.id === this.activeTab)) return g.id;
      }
      return "";
    },
    currentTitle() {
      return this.tabs.find((tab) => tab.id === this.activeTab)?.label || "工作台";
    },
    hasActiveMaintenanceResult() {
      if (this.result) return true;
      const session = this.currentSession || {};
      const workflow = session.workflow_state || {};
      const taskId = String(session.task_id || workflow.task_id || "");
      const isGeneratedTask = taskId && taskId !== "draft" && !taskId.toLowerCase().includes("draft");
      const hasArtifacts = Boolean(
        session.primary_claim_card
        || session.tri_mro_alignment
        || (session.claim_cards || []).length
      );
      return Boolean(isGeneratedTask && hasArtifacts);
    },
    overviewPipelineStages() {
      const wf = this.workflowState || {};
      const hasResult = this.hasActiveMaintenanceResult;
      const gateState = String(wf.safety_gate?.status || "unknown").toUpperCase();
      return [
        { id: "input", label: "现场输入", icon: "camera", tab: "diagnosis", status: this.query.text ? "done" : "pending", statusLabel: this.query.text ? "已输入" : "等待", detail: "故障描述 + 图片上传" },
        { id: "evidence", label: "证据检索", icon: "search", tab: "evidence", status: hasResult ? "done" : "pending", statusLabel: hasResult ? "已完成" : "等待", detail: "手册 + 案例 + 图谱 + 视觉" },
        { id: "claim", label: "检修判断卡", icon: "file-badge-2", tab: "claim_list", status: hasResult ? "done" : "pending", statusLabel: hasResult ? "已生成" : "等待", detail: "判断卡 + 证据预算" },
        { id: "structure", label: "结构定位", icon: "cuboid", tab: "spatial", status: hasResult ? "ready" : "pending", statusLabel: hasResult ? "可定位" : "等待", detail: "结构模型部件绑定" },
        { id: "sop", label: "SOP 作业票", icon: "list-checks", tab: "safety", status: hasResult ? "done" : "pending", statusLabel: hasResult ? "已生成" : "等待", detail: "标准化作业步骤" },
        { id: "gate", label: "安全闸门", icon: "shield-alert", tab: "safety", status: !hasResult ? "pending" : gateState === "BLOCKED" ? "blocked" : gateState === "READY" ? "ready" : "warning", statusLabel: hasResult ? this.gateStateDisplayLabel(gateState) : "等待", detail: "断电 / 泄压 / PPE" },
        { id: "knowledge", label: "知识沉淀", icon: "database", tab: "cases", status: "pending", statusLabel: "等待", detail: "案例 → 审核 → 图谱更新" },
      ];
    },
    overviewRiskCounts() {
      const risk = this.result?.risk_level || "unknown";
      return {
        high: risk === "high" ? 1 : 0,
        medium: risk === "medium" ? 1 : 0,
        low: risk === "low" || risk === "unknown" ? (this.result ? 1 : 0) : 0,
      };
    },
    overviewQuickMetrics() {
      const m = this.metrics?.latest || {};
      const inn = this.innovationMetricsList || [];
      const recall = m.recall_at_5 != null ? Math.round(m.recall_at_5 * 100) + "%" : "--";
      const alignment = inn.find((i) => i.label?.includes("对齐"))?.percent || "--";
      const blocking = inn.find((i) => i.label?.includes("阻断"))?.percent || "--";
      return { recall, alignment: alignment + (alignment !== "--" ? "%" : ""), blocking: blocking + (blocking !== "--" ? "%" : "") };
    },
    resourcePages() {
      return [
        {
          id: "comparison",
          icon: "bar-chart-3",
          label: "四组对比评测",
          summary: "对比无 RAG、文本 RAG、多模态 RAG、Tri-MRO 完整系统，证明三链对齐带来的改进。",
          actionLabel: "运行对比评测",
        },
        {
          id: "ingest",
          icon: "file-input",
          label: "入库手册",
          summary: "扫描 data/raw/manuals 中的 PDF/TXT/MD，抽取文本、页码和来源信息并写入知识库。",
          actionLabel: "执行手册入库",
        },
        {
          id: "index",
          icon: "database-zap",
          label: "重建索引",
          summary: "基于当前手册、案例和视觉标签重建检索索引，保证后续检修判断卡能引用最新证据。",
          actionLabel: "重建检索索引",
        },
        {
          id: "samples",
          icon: "layers-3",
          label: "生成样例",
          summary: "补齐电机、泵、轴承、发动机黄金样例，用于演示、回归和内部评测。",
          actionLabel: "生成演示样例",
        },
        {
          id: "quick_eval",
          icon: "activity",
          label: "快速评测",
          summary: "抽取少量题目快速检查检索、引用、SOP、安全闸门和拒答策略是否正常。",
          actionLabel: "运行快速评测",
        },
        {
          id: "full_eval",
          icon: "timer",
          label: "完整评测",
          summary: "运行完整评测集，产出前五召回率、三链对齐覆盖率、安全阻断率等核心指标。",
          actionLabel: "运行完整评测",
        },
        {
          id: "models",
          icon: "cpu",
          label: "探测模型",
          summary: "检查各模型供应商、路由能力、密钥状态和兜底情况，定位模型接口问题。",
          actionLabel: "探测可用模型",
        },
      ];
    },
    activeResourcePageMeta() {
      return this.resourcePages.find((item) => item.id === this.activeResourcePage) || this.resourcePages[0];
    },
    resourcePageStats() {
      const benchmarks = this.metrics?.benchmarks || [];
      const resources = this.resourceVerification?.resources || [];
      const latest = this.metrics?.latest || {};
      return {
        comparisonGroups: benchmarks.length || 4,
        manuals: resources.filter((item) => /manual/i.test(item.type || "") || /手册/.test(item.title || item.id || "")).length,
        verifiedResources: this.resourceVerification?.summary?.verified || 0,
        totalResources: this.resourceVerification?.summary?.total || 0,
        visualAssets: this.visualAssets.length || 0,
        modelProviders: this.modelResults.length || this.providers.length || 0,
        latestEval: latest.status || latest.run_id || "等待评测",
      };
    },
    resourceOperationView() {
      const meta = this.activeResourcePageMeta || {};
      const activeType = this.activeResourcePage;
      const entry = this.resourceOperationResult?.type === activeType ? this.resourceOperationResult : null;
      const clamp = (value) => Math.max(0, Math.min(100, Number.isFinite(Number(value)) ? Number(value) : 0));
      const numeric = (value, fallback = 0) => (Number.isFinite(Number(value)) ? Number(value) : fallback);
      const percentValue = (value) => {
        const number = numeric(value);
        return clamp(number <= 1 ? number * 100 : number);
      };
      const percent = (value) => `${Math.round(percentValue(value))}%`;
      const card = (label, value, note = "", tone = "info") => ({ label, value, note, tone });
      const bar = (label, rawValue, note = "", tone = "brand", options = {}) => {
        const isPercent = options.percent !== false;
        const max = Math.max(1, Number(options.max || 100));
        const value = isPercent ? percentValue(rawValue) : numeric(rawValue);
        const width = isPercent ? clamp(value) : clamp((value / max) * 100);
        return {
          label,
          note,
          tone,
          width: `${Math.max(width, value > 0 ? 7 : 0)}%`,
          valueLabel: isPercent ? `${Math.round(value)}%` : String(rawValue ?? 0),
        };
      };
      const row = (cells, tone = "") => ({ cells, tone });
      const base = {
        type: activeType,
        title: meta.label || "资源操作结果",
        subtitle: meta.summary || "运行操作后在这里显示结构化结果。",
        status: entry?.status || "idle",
        statusLabel: entry?.status === "running" ? "运行中" : entry ? "已完成" : "待运行",
        completedAt: entry?.completedAt || "",
        empty: !entry || entry.status === "running",
        cards: [],
        bars: [],
        tableHeaders: [],
        rows: [],
        notes: [],
      };
      if (!entry || entry.status === "running") {
        return {
          ...base,
          cards: [
            card("当前操作", meta.label || "--", entry?.status === "running" ? "接口任务正在执行" : "点击运行后显示结果"),
            card("展示方式", "图表化", "指标卡、条形图和明细表"),
            card("原始输出", "已隐藏", "不再占用黑色 JSON 框"),
          ],
          notes: [
            entry?.status === "running"
              ? "任务完成后会自动切换为对应的结构化结果图。"
              : "选择左侧资源操作并运行，系统会按返回字段自动生成可读结果。",
          ],
        };
      }

      const payload = entry.payload || {};
      if (entry.type === "comparison") {
        const benchmarks = Array.isArray(payload.benchmarks) ? payload.benchmarks : [];
        const full = benchmarks.find((item) => item.mode === "full_system") || benchmarks[benchmarks.length - 1] || {};
        return {
          ...base,
          empty: false,
          cards: [
            card("评测题目", `${payload.question_count || 0}/${payload.question_total || 0}`, payload.review_basis || "approved_only"),
            card("对比组", benchmarks.length || 0, "无 RAG / 文本 RAG / 多模态 RAG / Tri-MRO"),
            card("Tri-MRO Recall@5", percent(full.recall_at_5), "完整系统检索命中"),
            card("安全漏检率", percent(full.safety_miss_rate), "越低越好", "danger"),
          ],
          bars: benchmarks.map((item, index) => bar(
            item.name || item.mode || `方案 ${index + 1}`,
            item.recall_at_5,
            `引用 ${percent(item.citation_coverage)} · SOP ${percent(item.sop_score)}`,
            ["muted", "blue", "amber", "brand"][index] || "brand",
          )),
          tableHeaders: ["方案", "Recall@5", "引用覆盖", "SOP", "幻觉率", "安全漏检"],
          rows: benchmarks.map((item) => row([
            item.name || item.mode || "--",
            percent(item.recall_at_5),
            percent(item.citation_coverage),
            percent(item.sop_score),
            percent(item.hallucination_rate),
            percent(item.safety_miss_rate),
          ])),
          notes: [`生成时间：${payload.generated_at || entry.completedAt}`, `评测口径：${payload.review_basis || "--"}`],
        };
      }

      if (entry.type === "quick_eval" || entry.type === "full_eval") {
        const categoryBreakdown = payload.category_breakdown || payload.categories || {};
        const categoryRows = Array.isArray(categoryBreakdown)
          ? categoryBreakdown.map((item) => row([
            item.category || item.name || "--",
            item.question_count ?? item.count ?? "--",
            percent(item.recall_at_5),
            percent(item.citation_coverage),
          ]))
          : Object.entries(categoryBreakdown).map(([name, item]) => row([
            name,
            item?.question_count ?? item?.count ?? "--",
            percent(item?.recall_at_5),
            percent(item?.citation_coverage),
          ]));
        return {
          ...base,
          empty: false,
          cards: [
            card("评测题目", `${payload.question_count || 0}/${payload.question_total || 0}`, payload.review_basis || "approved_only"),
            card("Recall@5", percent(payload.recall_at_5), "前五召回命中率"),
            card("引用覆盖", percent(payload.citation_coverage), "答案引用证据比例"),
            card("安全通过", percent(1 - numeric(payload.safety_miss_rate)), "未漏检安全项", "success"),
          ],
          bars: [
            bar("检索召回", payload.recall_at_5, "命中可解释证据"),
            bar("引用覆盖", payload.citation_coverage, "回答是否带来源", "blue"),
            bar("SOP 完整度", payload.sop_score, "作业步骤覆盖", "brand"),
            bar("低幻觉表现", 1 - numeric(payload.hallucination_rate), "越高代表幻觉越少", "success"),
            bar("安全闸门表现", 1 - numeric(payload.safety_miss_rate), "越高代表漏检越少", "amber"),
          ],
          tableHeaders: categoryRows.length ? ["类别", "题量", "Recall@5", "引用覆盖"] : [],
          rows: categoryRows,
          notes: [`运行模式：${entry.type === "quick_eval" ? "快速评测" : "完整评测"}`, `完成时间：${entry.completedAt}`],
        };
      }

      if (entry.type === "ingest") {
        const documents = Array.isArray(payload.documents) ? payload.documents : [];
        const statusCounts = documents.reduce((acc, item) => {
          const status = item.status || "unknown";
          acc[status] = (acc[status] || 0) + 1;
          return acc;
        }, {});
        const chunkTotal = documents.reduce((sum, item) => sum + numeric(item.chunks), 0);
        const maxCount = Math.max(...Object.values(statusCounts), chunkTotal, numeric(payload.count), 1);
        return {
          ...base,
          empty: false,
          cards: [
            card("扫描文档", payload.count ?? documents.length, payload.directory || "data/raw/manuals"),
            card("切分片段", chunkTotal, "可被检索的手册片段"),
            card("新增入库", statusCounts.inserted || statusCounts.created || 0, "本次新写入文档", "success"),
            card("已存在", statusCounts.existing || statusCounts.skipped || 0, "无需重复写入"),
          ],
          bars: [
            ...Object.entries(statusCounts).map(([label, count]) => bar(label, count, "文档状态分布", label === "failed" ? "danger" : "brand", { percent: false, max: maxCount })),
            bar("索引-手册", payload.index?.manual, "重建后手册索引量", "blue", { percent: false, max: Math.max(maxCount, numeric(payload.index?.manual), 1) }),
            bar("本地向量", payload.index?.local_count, "本地嵌入批次", "amber", { percent: false, max: Math.max(maxCount, numeric(payload.index?.local_count), 1) }),
          ],
          tableHeaders: ["文档", "设备", "状态", "片段"],
          rows: documents.map((item) => row([
            item.document_id || item.path || "--",
            item.equipment || "--",
            item.status || "--",
            item.chunks ?? "--",
          ])),
          notes: [`入库目录：${payload.directory || "--"}`, `完成时间：${entry.completedAt}`],
        };
      }

      if (entry.type === "index") {
        const failed = Array.isArray(payload.failed_batches) ? payload.failed_batches : [];
        const maxCount = Math.max(numeric(payload.manual), numeric(payload.case), numeric(payload.remote_count), numeric(payload.local_count), 1);
        return {
          ...base,
          empty: false,
          cards: [
            card("手册索引", payload.manual ?? 0, "手册知识片段"),
            card("案例索引", payload.case ?? 0, "案例知识片段"),
            card("本地嵌入", payload.local_count ?? 0, "本地向量生成"),
            card("远程嵌入", payload.remote_count ?? 0, payload.remote_used ? "已使用远程模型" : "未使用远程模型", payload.remote_used ? "success" : "info"),
          ],
          bars: [
            bar("手册", payload.manual, "手册向量规模", "brand", { percent: false, max: maxCount }),
            bar("案例", payload.case, "案例向量规模", "blue", { percent: false, max: maxCount }),
            bar("本地嵌入", payload.local_count, "本地生成数量", "amber", { percent: false, max: maxCount }),
            bar("远程嵌入", payload.remote_count, "远程生成数量", "success", { percent: false, max: maxCount }),
          ],
          tableHeaders: ["批次", "状态", "说明"],
          rows: failed.length
            ? failed.map((item, index) => row([`#${index + 1}`, "失败", item.error || item.message || JSON.stringify(item)], "danger"))
            : [row(["全部批次", "完成", "未返回失败批次"], "success")],
          notes: [`嵌入模型：${payload.model || "--"}`, `完成时间：${entry.completedAt}`],
        };
      }

      if (entry.type === "samples") {
        const targetCases = numeric(payload.target_cases);
        const targetQuestions = numeric(payload.target_eval_questions);
        return {
          ...base,
          empty: false,
          cards: [
            card("新增案例", payload.inserted_cases ?? 0, `目标 ${payload.target_cases ?? "--"}`),
            card("新增评测题", payload.inserted_eval_questions ?? 0, `目标 ${payload.target_eval_questions ?? "--"}`),
            card("手册索引", payload.index?.manual ?? 0, "样例生成后索引状态"),
            card("案例索引", payload.index?.case ?? 0, payload.note || "可用于演示和回归", "success"),
          ],
          bars: [
            bar("案例补齐", targetCases ? numeric(payload.inserted_cases) / targetCases : 0, "新增案例 / 目标案例", "brand"),
            bar("题库补齐", targetQuestions ? numeric(payload.inserted_eval_questions) / targetQuestions : 0, "新增题目 / 目标题目", "blue"),
            bar("手册索引", payload.index?.manual, "当前手册索引量", "amber", { percent: false, max: Math.max(numeric(payload.index?.manual), numeric(payload.index?.case), 1) }),
            bar("案例索引", payload.index?.case, "当前案例索引量", "success", { percent: false, max: Math.max(numeric(payload.index?.manual), numeric(payload.index?.case), 1) }),
          ],
          tableHeaders: ["项目", "新增", "目标", "说明"],
          rows: [
            row(["黄金案例", payload.inserted_cases ?? 0, payload.target_cases ?? "--", "用于演示和案例检索"]),
            row(["评测题", payload.inserted_eval_questions ?? 0, payload.target_eval_questions ?? "--", "用于回归评测"]),
          ],
          notes: [payload.note || "样例生成完成。", `完成时间：${entry.completedAt}`],
        };
      }

      if (entry.type === "models") {
        const results = Array.isArray(payload.results) ? payload.results : [];
        const okCount = results.filter((item) => item.ok).length;
        const modelCount = results.reduce((sum, item) => sum + (Array.isArray(item.models) ? item.models.length : 0), 0);
        const maxModels = Math.max(...results.map((item) => Array.isArray(item.models) ? item.models.length : 0), 1);
        return {
          ...base,
          empty: false,
          cards: [
            card("供应商", results.length, "已探测路由"),
            card("可用供应商", okCount, "接口可正常响应", okCount ? "success" : "danger"),
            card("模型数量", modelCount, "返回的可用模型"),
            card("智能体路由", this.agentRoutes.length, "工作台已配置路由"),
          ],
          bars: results.map((item) => bar(
            item.provider || item.name || "--",
            Array.isArray(item.models) ? item.models.length : 0,
            item.ok ? "可用" : (item.error || "异常"),
            item.ok ? "success" : "danger",
            { percent: false, max: maxModels },
          )),
          tableHeaders: ["供应商", "状态", "模型数", "说明"],
          rows: results.map((item) => row([
            item.provider || item.name || "--",
            item.ok ? "可用" : "异常",
            Array.isArray(item.models) ? item.models.length : 0,
            item.error || (Array.isArray(item.models) ? item.models.slice(0, 3).join(" / ") : "--"),
          ], item.ok ? "success" : "danger")),
          notes: [`完成时间：${entry.completedAt}`, "异常供应商会保留错误原因，便于定位密钥、网络或模型名问题。"],
        };
      }

      return {
        ...base,
        empty: false,
        cards: [
          card("操作完成", meta.label || entry.type, "返回内容已结构化保存"),
          card("字段数量", Object.keys(payload).length, "顶层返回字段"),
          card("完成时间", entry.completedAt || "--", "最近一次运行"),
        ],
        tableHeaders: ["字段", "内容"],
        rows: Object.entries(payload).slice(0, 12).map(([key, value]) => row([
          key,
          typeof value === "object" ? JSON.stringify(value) : String(value),
        ])),
        notes: ["该操作暂未配置专属图表，已用通用摘要展示。"],
      };
    },
    resourceDashboardCategories() {
      const rv = this.resourceVerification || {};
      const resources = rv.resources || [];
      const manualCount = resources.filter((r) => /manual/i.test(r.type || "") || /手册/.test(r.title || r.id || "")).length;
      const manualVerified = resources.filter((r) => (/manual/i.test(r.type || "") || /手册/.test(r.title || r.id || "")) && r.verify_status === "verified").length;
      const threed = rv.three_d_assets || [];
      const threedVerified = rv.summary?.authorized_3d_verified || 0;
      const threedTotal = rv.summary?.authorized_3d_assets || threed.length || 0;
      const cadTotal = this.candidateCadSummary?.total || 0;
      const cadApproved = this.candidateCadSummary?.approved_candidate || 0;
      const partTotal = (this.partTreeCandidates.candidates || []).length;
      const caseCount = this.pendingCases.length;
      const feedbackCount = this.feedbackRecords.length;
      return [
        { id: "manuals", icon: "book-open", label: "维修手册", count: manualCount, verified: manualVerified, total: manualCount, color: "#0f766e", desc: "PDF/TXT/MD 技术手册，入库后拆分为可检索文档块" },
        { id: "3d", icon: "cuboid", label: "3D 模型资产", count: threedTotal, verified: threedVerified, total: threedTotal, color: "#6366f1", desc: "授权 STEP/GLB 模型，用于 CAD 结构工位空间定位" },
        { id: "visual", icon: "image", label: "视觉资产", count: this.visualAssets.length, verified: this.visualAssets.filter((a) => a.caption).length, total: this.visualAssets.length, color: "#f59e0b", desc: "现场照片与 VLM/OCR 标注，支撑图片识别与证据链" },
        { id: "cad", icon: "box", label: "候选 CAD", count: cadTotal, verified: cadApproved, total: cadTotal, color: "#ec4899", desc: "照片驱动生成的候选 CAD 产物，经机械审核后晋升" },
        { id: "parts", icon: "git-branch", label: "零件树候选", count: partTotal, verified: (this.partTreeCandidates.candidates || []).filter((c) => c.status === "verified").length, total: partTotal, color: "#8b5cf6", desc: "CAD 装配树解析的零件层次结构与辅助标注绑定" },
        { id: "knowledge", icon: "brain", label: "知识沉淀", count: caseCount + feedbackCount, verified: caseCount, total: caseCount + feedbackCount, color: "#06b6d4", desc: "待审核案例与反馈记录，构成知识闭环写入图谱" },
      ];
    },
    resourceDashboardTopStats() {
      const rv = this.resourceVerification?.summary || {};
      const resources = this.resourceVerification?.resources || [];
      return [
        { label: "资源总数", value: rv.total || resources.length || 0, icon: "database" },
        { label: "已验证", value: rv.verified || 0, icon: "check-circle-2" },
        { label: "被阻断", value: rv.blocked || 0, icon: "alert-triangle" },
        { label: "视觉资产", value: this.visualAssets.length, icon: "image" },
        { label: "3D 资产", value: rv.authorized_3d_assets || 0, icon: "cuboid" },
        { label: "智能体路由", value: this.agentRoutes.length, icon: "cpu" },
      ];
    },
    agentPipelineRoles() {
      const routeMap = {};
      (this.agentRoutes || []).forEach((r) => { routeMap[r.label] = r; });
      return [
        { id: "vision", label: "现场感知", icon: "eye", role: "视觉分析", route: routeMap["vision"] || routeMap["Visual Analysis"] || this.agentRoutes[1] },
        { id: "text", label: "文本推理", icon: "brain", role: "检索+SOP", route: routeMap["text"] || routeMap["Text Reasoning"] || this.agentRoutes[0] },
        { id: "embedding", label: "语义嵌入", icon: "layers", role: "向量检索", route: routeMap["embedding"] || routeMap["Embedding"] || this.agentRoutes[2] },
        { id: "compliance", label: "合规校验", icon: "shield-check", role: "安全闸门", route: routeMap["compliance"] || routeMap["Compliance"] || this.agentRoutes[3] },
        { id: "knowledge", label: "知识写入", icon: "pen-tool", role: "图谱更新", route: routeMap["knowledge"] || routeMap["Knowledge Write"] || this.agentRoutes[4] },
      ];
    },
    workflowState() {
      if (this.result?.workflow_state) return this.result.workflow_state;
      if (this.hasActiveMaintenanceResult && this.currentSession?.workflow_state) return this.currentSession.workflow_state;
      return {
        task_id: "draft",
        equipment: "",
        model: "",
        selected_component_keys: [],
        selected_model_component_keys: [],
        stages: [],
        safety_gate: { status: "not_started", label: "等待生成检修任务", blocking_items: [] },
      };
    },
    workflowStages() {
      return this.workflowState.stages || [];
    },
    workflowStageSummary() {
      const stages = this.workflowStages;
      if (!stages.length) return "现场输入 → 证据链 → 结构链 → 作业链 → 安全闸门 → 案例沉淀";
      return stages.map((item) => `${item.label}:${item.status}`).join(" / ");
    },
    agentProgressBlueprint() {
      return [
        { id: "vision", label: "现场感知智能体", detail: "汇总设备型号、文本故障、文字与图像识别线索" },
        { id: "retrieval", label: "证据检索智能体", detail: "召回手册、案例、图谱路径和视觉证据" },
        { id: "claim", label: "判断卡智能体", detail: "计算证据预算，生成可追溯判断卡" },
        { id: "cad", label: "结构定位智能体", detail: "映射部件键并准备 CAD 工位高亮" },
        { id: "sop", label: "作业票智能体", detail: "生成标准作业票、工具备件与验收标准" },
        { id: "safety", label: "安全闸门智能体", detail: "检查断电、泄压、PPE 等安全闸门" },
      ];
    },
    agentProgressSteps() {
      const steps = this.agentProgressBlueprint;
      const active = Math.min(this.agentProgressIndex, steps.length - 1);
      return steps.map((step, index) => {
        let state = "pending";
        if (this.loading) {
          state = index < active ? "done" : index === active ? "active" : "pending";
        } else if (this.result) {
          state = "done";
        }
        return { ...step, state };
      });
    },
    currentAgentProgressStep() {
      return this.agentProgressSteps.find((step) => step.state === "active")
        || this.agentProgressSteps[this.agentProgressSteps.length - 1]
        || {};
    },
    agentProgressPercent() {
      const total = this.agentProgressBlueprint.length || 1;
      if (this.result && !this.loading) return 100;
      return Math.min(98, Math.round(((this.agentProgressIndex + 1) / total) * 100));
    },
    triMroAlignment() {
      return this.result?.tri_mro_alignment || this.currentSession?.tri_mro_alignment || null;
    },
    triMroStatusLabel() {
      const status = this.triMroAlignment?.alignment_status || "needs_review";
      return {
        complete: "三链对齐",
        partial: "部分对齐",
        blocked: "安全阻断",
        needs_review: "需复核",
      }[status] || status;
    },
    triMroEvidencePreview() {
      const evidence = this.triMroAlignment?.evidence_chain || [];
      if (!evidence.length) return "暂无可追溯证据，系统应要求补充资料或转人工复核。";
      return evidence
        .slice(0, 3)
        .map((item) => item.title || item.summary || item.source_type)
        .join(" / ");
    },
    primaryClaimCard() {
      return this.result?.primary_claim_card || this.currentSession?.primary_claim_card || null;
    },
    claimCards() {
      return this.result?.claim_cards || this.currentSession?.claim_cards || [];
    },
    claimDecisionLabel() {
      const decision = this.primaryClaimCard?.evidence_budget?.decision || "pending";
      return {
        answer: "可输出明确判断",
        confirm: "可能判断，需要人工确认",
        direction_only: "仅给排查方向",
        refuse: "证据不足，拒绝确定结论",
        pending: "等待证据预算",
      }[decision] || decision;
    },
    claimEvidenceScorePercent() {
      return Math.round((this.primaryClaimCard?.evidence_budget?.score || 0) * 100);
    },
    evidenceBudgetRows() {
      const budget = this.primaryClaimCard?.evidence_budget || {};
      const sourceScores = budget.source_scores || {};
      return [
        { key: "manual", label: "E1 手册证据", value: sourceScores.manual || 0, count: this.manualEvidenceDetails.length, note: "检修规程、通用安全规范和引用段落" },
        { key: "case", label: "E2 案例证据", value: sourceScores.case || 0, count: this.caseEvidenceDetails.length, note: "相似故障案例和历史处置记录" },
        { key: "graph", label: "E3 图谱路径", value: sourceScores.graph || 0, count: this.graphPathEvidenceDetails.length, note: "设备、部件、故障、SOP、合规关系路径" },
        { key: "visual", label: "E4 视觉证据", value: sourceScores.visual || 0, count: this.visualEvidenceDetails.length, note: "VLM/OCR/结构化图片资产" },
      ];
    },
    manualEvidenceDetails() {
      const citations = this.result?.citations || this.triMroAlignment?.evidence_budget?.manual_refs || [];
      return citations.slice(0, 6).map((item, index) => ({
        id: item.evidence_id || item.id || `manual_${index}`,
        title: item.title || item.source || "手册引用",
        summary: item.content || item.summary || item.section || "命中检修规程片段",
        meta: [item.section, item.page ? `P${item.page}` : "", item.confidence != null ? `${Math.round(item.confidence * 100)}%` : ""].filter(Boolean).join(" · "),
        source: item.source || item.source_url || "本地手册库",
      }));
    },
    caseEvidenceDetails() {
      const cases = this.result?.similar_cases || this.triMroAlignment?.evidence_budget?.case_refs || [];
      return cases.slice(0, 6).map((item, index) => ({
        id: item.evidence_id || item.id || `case_${index}`,
        title: item.title || item.fault_type || "相似案例",
        summary: item.actions || item.symptoms || item.summary || item.content || "历史处置记录与当前故障相似",
        meta: [item.model, item.equipment, item.similarity_score != null ? `${Math.round(item.similarity_score * 100)}%` : ""].filter(Boolean).join(" · "),
        source: item.source || "案例库",
      }));
    },
    graphPathEvidenceDetails() {
      const paths = this.result?.graph_paths || [];
      return paths.slice(0, 6).map((item, index) => ({
        id: item.evidence_id || `graph_${index}`,
        title: (item.path || []).join(" → ") || item.source_title || "图谱路径",
        summary: [item.source_title, (item.safety_neighbors || []).join("、")].filter(Boolean).join("；") || "知识图谱中的可解释关系路径",
        meta: item.confidence != null ? `${Math.round(item.confidence * 100)}%` : "",
        source: "知识图谱",
      }));
    },
    visualEvidenceDetails() {
      const resultItems = this.result?.visual_evidence || [];
      const assetItems = (this.visualAssets || [])
        .filter((asset) => !this.query.visual_asset_id || Number(asset.id) === Number(this.query.visual_asset_id) || asset.equipment === this.query.equipment)
        .slice(0, 4)
        .map((asset) => ({
          id: asset.id,
          title: asset.filename || `视觉资产 #${asset.id}`,
          summary: asset.caption || asset.analysis?.caption || "结构化视觉资产",
          meta: [asset.provider, asset.model, asset.review_status].filter(Boolean).join(" · "),
          source: asset.stored_path || asset.source_url || "",
          image_url: this.visualAssetImageUrl(asset),
          asset,
        }));
      const merged = [
        ...resultItems.map((item, index) => ({
          id: item.evidence_id || item.id || `visual_result_${index}`,
          title: item.title || "视觉证据",
          summary: item.caption || item.summary || "图片疑似显示故障相关特征",
          meta: [item.source, item.confidence != null ? `${Math.round(item.confidence * 100)}%` : ""].filter(Boolean).join(" · "),
          source: item.source || "",
          image_url: item.visual_asset_id ? `/api/visual-assets/${item.visual_asset_id}/file` : "",
        })),
        ...assetItems,
      ];
      const seen = new Set();
      return merged.filter((item) => {
        const key = item.id || item.title;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }).slice(0, 8);
    },
    evidenceWorkbenchGroups() {
      return [
        { key: "manual", label: "手册证据", icon: "book-open-check", items: this.manualEvidenceDetails },
        { key: "case", label: "案例证据", icon: "clipboard-check", items: this.caseEvidenceDetails },
        { key: "graph", label: "图谱路径", icon: "network", items: this.graphPathEvidenceDetails },
        { key: "visual", label: "视觉路径", icon: "image", items: this.visualEvidenceDetails },
      ];
    },
    activeEvidenceItems() {
      return this.evidenceWorkbenchGroups.find((group) => group.key === this.activeEvidenceGroup)?.items || [];
    },
    activeEvidenceGroupLabel() {
      return this.evidenceWorkbenchGroups.find((group) => group.key === this.activeEvidenceGroup)?.label || "证据";
    },
    evidenceBudgetDetails() {
      return this.evidenceBudgetRows.map((row) => ({
        ...row,
        percent: Math.round(row.value * 100),
        items: {
          manual: this.manualEvidenceDetails,
          case: this.caseEvidenceDetails,
          graph: this.graphPathEvidenceDetails,
          visual: this.visualEvidenceDetails,
        }[row.key] || [],
      }));
    },
    activeComponentContract() {
      return this.activeSpatialGuidance?.component_contract
        || this.primaryClaimCard?.structure_chain?.component_contract
        || null;
    },
    componentContractGateLabels() {
      return this.activeComponentContract?.required_gates || this.primaryClaimCard?.safety_gate?.required_gates || [];
    },
    componentContractGateDisplayLabels() {
      return this.componentContractGateLabels.map((item) => this.formatGateLabel(item));
    },
    claimFmeaItems() {
      const fmea = this.primaryClaimCard?.fmea_risk_chain || {};
      const sources = {
        failure_mode: "故障描述、视觉标签和手册故障模式共同命中",
        severity: "涉及拆卸、残余能量和泄漏污染，安全后果较高",
        occurrence: "相似案例与手册频次支持中等发生概率",
        detectability: "现场照片、泄漏痕迹和复测项目可辅助发现",
        risk_priority: "Severity × Occurrence × Detectability",
      };
      return [
        { key: "failure_mode", label: "失效模式", value: fmea.failure_mode || "待识别", source: sources.failure_mode },
        { key: "severity", label: "严重度", value: fmea.severity || 0, source: sources.severity },
        { key: "occurrence", label: "发生度", value: fmea.occurrence || 0, source: sources.occurrence },
        { key: "detectability", label: "可探测度", value: fmea.detectability || 0, source: sources.detectability },
        { key: "risk_priority", label: "风险优先数", value: fmea.risk_priority || 0, source: sources.risk_priority },
      ];
    },
    claimSafetyAuditTrail() {
      return this.primaryClaimCard?.safety_gate?.audit_trail || [];
    },
    knowledgeWritePipeline() {
      return this.latestKnowledgeWrite || null;
    },
    innovationMetricsList() {
      const metrics = this.metrics?.tri_mro_innovation_metrics || {};
      return Object.entries(metrics).map(([key, item]) => ({
        key,
        label: item.label || key,
        value: item.value || 0,
        percent: Math.round((item.value || 0) * 100),
        explanation: item.explanation || "",
      }));
    },
    sessionEquipmentLabel() {
      if (!this.hasActiveMaintenanceResult) return "待选择设备";
      const equipment = this.workflowState.equipment || this.query.equipment;
      return this.graphFocusOptions.find((item) => item.id === equipment)?.label || equipment || "设备";
    },
    sessionComponentSummary() {
      if (!this.hasActiveMaintenanceResult) return "未开始检修";
      const keys = this.workflowState.selected_component_keys || [];
      return keys.length ? this.componentSummaryLabel(keys) : "待定位部件";
    },
    sessionComponentCompact() {
      if (!this.hasActiveMaintenanceResult) return "未开始";
      const keys = this.workflowState.selected_component_keys || [];
      return keys.length ? this.componentSummaryLabel(keys, 2) : "待定位部件";
    },
    sessionTaskLabel() {
      if (!this.hasActiveMaintenanceResult) return "未开始";
      return this.workflowState.task_id || "draft";
    },
    sessionModelLabel() {
      if (!this.hasActiveMaintenanceResult) return "等待生成检修任务";
      return this.workflowState.model || this.query.model || "未填写型号";
    },
    sessionContextLabel() {
      if (!this.hasActiveMaintenanceResult) return "等待生成检修任务";
      return `${this.sessionEquipmentLabel} · ${this.sessionComponentSummary}`;
    },
    graphFocusOptions() {
      return [
        { id: "motor", label: "电机" },
        { id: "pump", label: "离心泵" },
        { id: "bearing", label: "轴承" },
        { id: "engine", label: "发动机" },
      ];
    },
    graphLayerOptions() {
      return [
        { id: "Component", label: "部件" },
        { id: "Fault", label: "故障" },
        { id: "Cause", label: "原因" },
        { id: "Process", label: "SOP" },
        { id: "SafetyRule", label: "合规" },
        { id: "Case", label: "案例" },
        { id: "ManualChunk", label: "手册" },
        { id: "VisualAsset", label: "视觉" },
      ];
    },
    graphIndexes() {
      const nodes = this.graph.nodes || [];
      const edges = this.graph.edges || [];
      const byId = Object.fromEntries(nodes.map((node) => [node.id, node]));
      const outgoing = {};
      const incoming = {};
      const degree = {};
      edges.forEach((edge) => {
        outgoing[edge.source] = outgoing[edge.source] || [];
        incoming[edge.target] = incoming[edge.target] || [];
        outgoing[edge.source].push(edge);
        incoming[edge.target].push(edge);
        degree[edge.source] = (degree[edge.source] || 0) + 1;
        degree[edge.target] = (degree[edge.target] || 0) + 1;
      });
      return { nodes, edges, byId, outgoing, incoming, degree };
    },
    readableGraph() {
      const { nodes, edges, byId, degree } = this.graphIndexes;
      const focus = this.graphFocus || "motor";
      const focusPrefix = `${focus}:`;
      const focusEquipmentId = `equipment:${focus}`;
      const focusFaultIds = new Set(
        nodes
          .filter((node) => node.id?.startsWith(`fault:${focus}:`))
          .sort((a, b) => (degree[b.id] || 0) - (degree[a.id] || 0))
          .slice(0, 12)
          .map((node) => node.id),
      );
      const candidateIds = new Set([focusEquipmentId, ...focusFaultIds]);

      nodes.forEach((node) => {
        if (node.id?.startsWith(`component:${focus}:`) || node.id?.startsWith(`safety:${focus}:`)) {
          candidateIds.add(node.id);
        }
      });
      edges.forEach((edge) => {
        const sourceInFocus = edge.source === focusEquipmentId || edge.source?.includes(focusPrefix) || focusFaultIds.has(edge.source);
        const targetInFocus = edge.target === focusEquipmentId || edge.target?.includes(focusPrefix) || focusFaultIds.has(edge.target);
        if (sourceInFocus && byId[edge.target]) candidateIds.add(edge.target);
        if (targetInFocus && byId[edge.source]) candidateIds.add(edge.source);
      });

      const scored = [...candidateIds]
        .map((id) => byId[id])
        .filter(Boolean)
        .map((node) => ({
          ...node,
          score:
            (GRAPH_TYPE_WEIGHT[node.type] || 20) +
            (node.id === focusEquipmentId ? 120 : 0) +
            (node.id?.includes(focusPrefix) ? 30 : 0) +
            Math.min(30, degree[node.id] || 0),
        }))
        .sort((a, b) => b.score - a.score);
      const typeCounts = {};
      const selected = [];
      for (const node of scored) {
        const limit = GRAPH_TYPE_LIMIT[node.type] || 3;
        const currentCount = typeCounts[node.type] || 0;
        if (currentCount >= limit) continue;
        typeCounts[node.type] = currentCount + 1;
        selected.push(node);
        if (selected.length >= GRAPH_DISPLAY_LIMIT) break;
      }
      const visibleIds = new Set(selected.map((node) => node.id));
      const visibleEdges = edges
        .filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))
        .slice(0, GRAPH_EDGE_LIMIT);

      return { nodes: selected, edges: visibleEdges };
    },
    graphEvidenceChains() {
      const { nodes, edges, byId, outgoing, incoming, degree } = this.graphIndexes;
      const focus = this.graphFocus || "motor";
      const equipment = byId[`equipment:${focus}`] || { id: `equipment:${focus}`, label: this.graphFocusLabel, type: "Equipment" };
      const isVisibleType = (node) => !node || this.graphLayers[node.type] !== false;
      const uniqueNodes = (items) => {
        const seen = new Set();
        return items.filter((node) => {
          if (!node || seen.has(node.id) || !isVisibleType(node)) return false;
          seen.add(node.id);
          return true;
        });
      };
      const targets = (sourceId, relation, type = "") =>
        uniqueNodes(
          (outgoing[sourceId] || [])
            .filter((edge) => !relation || edge.relation === relation)
            .map((edge) => byId[edge.target])
            .filter((node) => !type || node?.type === type),
        );
      const sources = (targetId, relation, type = "") =>
        uniqueNodes(
          (incoming[targetId] || [])
            .filter((edge) => !relation || edge.relation === relation)
            .map((edge) => byId[edge.source])
            .filter((node) => !type || node?.type === type),
        );

      const focusComponents = uniqueNodes([
        ...targets(equipment.id, "HAS_COMPONENT", "Component"),
        ...nodes.filter((node) => node.id?.startsWith(`component:${focus}:`)),
      ])
        .filter((node) => !/^(设备|安全|通用|待确认部件)$/.test(String(node.label || "")))
        .sort((a, b) => (degree[b.id] || 0) - (degree[a.id] || 0))
        .slice(0, 7);
      const components = this.graphLayers.Component === false ? [equipment] : focusComponents.length ? focusComponents : [equipment];
      const chains = [];

      components.forEach((component) => {
        const directFaults = targets(component.id, "HAS_FAULT", "Fault");
        const fallbackFaults = nodes.filter((node) => node.id?.startsWith(`fault:${focus}:`));
        const allFaults = uniqueNodes(directFaults.length ? directFaults : component.id === equipment.id ? fallbackFaults : [])
          .sort((a, b) => (degree[b.id] || 0) - (degree[a.id] || 0))
        const specificFaults = allFaults.filter((fault) => !/通用检修/.test(String(fault.label || "")));
        const faults = (specificFaults.length ? specificFaults : allFaults).slice(0, 2);
        faults.forEach((fault) => {
          if (!isVisibleType(fault)) return;
          const causes = targets(fault.id, "HAS_CAUSE", "Cause").slice(0, 2);
          const actions = targets(fault.id, "HAS_STEP", "Process").slice(0, 2);
          const safety = targets(fault.id, "HAS_SAFETY_RULE", "SafetyRule").slice(0, 2);
          const manuals = sources(fault.id, "CITED_BY", "ManualChunk").slice(0, 3);
          const cases = sources(fault.id, "OBSERVED_IN", "Case").slice(0, 3);
          const visuals = uniqueNodes([
            ...sources(fault.id, "OBSERVED_IN", "VisualAsset"),
            ...sources(component.id, "HAS_COMPONENT", "VisualAsset"),
          ]).slice(0, 2);
          const evidence = [
            ...visuals.map((node) => ({ ...node, evidenceType: "视觉" })),
            ...manuals.map((node) => ({ ...node, evidenceType: "手册" })),
            ...cases.map((node) => ({ ...node, evidenceType: "案例" })),
          ].slice(0, 5);
          const actionNode = actions[0] || { id: `${fault.id}:sop`, label: "生成标准化 SOP", type: "Process" };
          const safetyNode = safety[0] || { id: `${fault.id}:safety`, label: "LOTO / PPE / 复测验收", type: "SafetyRule" };
          const causeNode = causes[0] || { id: `${fault.id}:cause`, label: cases[0]?.label || "结合手册与案例复核原因", type: "Cause" };
          const confidence = Math.min(98, 66 + Math.min(18, degree[fault.id] || 0) + evidence.length * 3);
          const specificFaultBonus = /通用检修/.test(String(fault.label || "")) ? 0 : 24;
          const evidenceBonus = Math.min(10, evidence.length * 2);
          const visualBonus = evidence.some((item) => item.type === "VisualAsset") ? 8 : 0;
          chains.push({
            id: `${component.id}__${fault.id}`,
            equipment,
            component,
            fault,
            cause: causeNode,
            action: actionNode,
            safety: safetyNode,
            evidence,
            confidence,
            score: confidence + specificFaultBonus + evidenceBonus + visualBonus,
            risk: this.inferGraphRisk(fault.label),
            steps: [
              { role: "设备", node: equipment, tone: "equipment" },
              { role: "部件", node: component, tone: "component" },
              { role: "故障", node: fault, tone: "fault" },
              { role: "原因", node: causeNode, tone: "cause" },
              { role: "SOP", node: actionNode, tone: "process" },
              { role: "合规", node: safetyNode, tone: "safety" },
            ],
          });
        });
      });

      const specificChains = chains.filter((chain) => !/通用检修/.test(String(chain.fault.label || "")));
      return (specificChains.length >= 4 ? specificChains : chains)
        .sort((a, b) => b.score - a.score)
        .slice(0, 8);
    },
    graphWorkbenchStats() {
      const chains = this.graphEvidenceChains;
      const evidenceCount = chains.reduce((sum, chain) => sum + chain.evidence.length, 0);
      const riskCount = chains.filter((chain) => chain.risk === "高").length;
      return [
        { label: "可解释链路", value: chains.length },
        { label: "证据引用", value: evidenceCount },
        { label: "高风险链路", value: riskCount },
      ];
    },
    selectedGraphNode() {
      const { byId } = this.graphIndexes;
      if (this.selectedGraphNodeId && byId[this.selectedGraphNodeId]) return byId[this.selectedGraphNodeId];
      if (this.selectedGraphNodeId) {
        const mapNode = this.graphMapNodes.find((node) => node.id === this.selectedGraphNodeId);
        if (mapNode) return { id: mapNode.id, label: mapNode.label || mapNode.displayLabel, type: mapNode.type };
      }
      return null;
    },
    selectedGraphConnections() {
      const node = this.selectedGraphNode;
      if (!node) return [];
      const { byId, outgoing, incoming } = this.graphIndexes;
      const out = (outgoing[node.id] || []).map((edge) => ({
        direction: "out",
        relation: edge.relation,
        node: byId[edge.target],
      }));
      const inc = (incoming[node.id] || []).map((edge) => ({
        direction: "in",
        relation: edge.relation,
        node: byId[edge.source],
      }));
      return [...out, ...inc].filter((item) => item.node).slice(0, 10);
    },
    selectedGraphEvidence() {
      const node = this.selectedGraphNode;
      if (!node) return [];
      return this.graphEvidenceChains
        .filter((chain) => chain.steps.some((step) => step.node.id === node.id) || chain.evidence.some((item) => item.id === node.id))
        .flatMap((chain) => chain.evidence)
        .slice(0, 6);
    },
    legacyGraphMapNodes() {
      const baseNodes = [];
      const center = {
        id: "current-task",
        label: this.sessionEquipmentLabel,
        type: "Task",
        x: 50,
        y: 50,
        size: 78,
        tone: "task",
      };
      baseNodes.push(center);
      const chains = this.graphEvidenceChains.slice(0, 5);
      const components = [];
      const evidenceNodes = [];
      chains.forEach((chain) => {
        components.push(chain.component);
        evidenceNodes.push(chain.fault, chain.action, chain.safety, ...chain.evidence.slice(0, 2));
      });
      const unique = (items) => {
        const seen = new Set();
        return items.filter((item) => {
          if (!item || seen.has(item.id)) return false;
          seen.add(item.id);
          return true;
        });
      };
      const orbit = [
        ...unique(components).slice(0, 4).map((node) => ({ ...node, tone: "component", size: 58 })),
        ...unique(evidenceNodes).slice(0, 10).map((node) => ({
          ...node,
          tone: node.type === "Fault" ? "fault" : node.type === "VisualAsset" ? "visual" : node.type === "SafetyRule" ? "safety" : "evidence",
          size: node.type === "Fault" ? 54 : 44,
        })),
      ];
      const radius = 36;
      orbit.forEach((node, index) => {
        const angle = (-90 + (360 / Math.max(1, orbit.length)) * index) * (Math.PI / 180);
        baseNodes.push({
          ...node,
          x: Math.round(50 + Math.cos(angle) * radius),
          y: Math.round(50 + Math.sin(angle) * radius),
        });
      });
      return baseNodes;
    },
    legacyGraphMapEdges() {
      const nodes = this.graphMapNodes;
      const byId = Object.fromEntries(nodes.map((node) => [node.id, node]));
      const nodeIds = new Set(nodes.map((node) => node.id));
      const edges = [];
      this.graphEvidenceChains.slice(0, 5).forEach((chain) => {
        if (nodeIds.has(chain.component.id)) edges.push({ id: `task-${chain.component.id}`, source: "current-task", target: chain.component.id, label: "定位到" });
        if (nodeIds.has(chain.fault.id)) edges.push({ id: `${chain.component.id}-${chain.fault.id}`, source: chain.component.id, target: chain.fault.id, label: "可能故障" });
        [chain.action, chain.safety, ...chain.evidence.slice(0, 2)].forEach((node) => {
          if (nodeIds.has(node.id) && nodeIds.has(chain.fault.id)) {
            edges.push({ id: `${chain.fault.id}-${node.id}`, source: chain.fault.id, target: node.id, label: node.evidenceType || this.graphTypeLabel(node.type) });
          }
        });
      });
      return edges.slice(0, 18).map((edge) => ({
        ...edge,
        x1: byId[edge.source]?.x || 50,
        y1: byId[edge.source]?.y || 50,
        x2: byId[edge.target]?.x || 50,
        y2: byId[edge.target]?.y || 50,
      }));
    },
    graphLaneColumns() {
      return [
        { id: "task", label: "任务入口", caption: this.graphFocusLabel, x: 88, width: 150 },
        { id: "component", label: "结构部件", caption: "CAD / 视觉定位", x: 274, width: 166 },
        { id: "fault", label: "故障模式", caption: "风险归因", x: 470, width: 166 },
        { id: "evidence", label: "证据来源", caption: "手册 / 案例 / 视觉", x: 680, width: 178 },
        { id: "decision", label: "SOP 与安全", caption: "作业步骤 / 闸门", x: 888, width: 184 },
      ];
    },
    graphMapNodes() {
      const chains = this.graphEvidenceChains.slice(0, 6);
      const laneOrder = ["task", "component", "fault", "evidence", "decision"];
      const laneMeta = Object.fromEntries(this.graphLaneColumns.map((lane) => [lane.id, lane]));
      const laneBuckets = Object.fromEntries(laneOrder.map((lane) => [lane, []]));
      const laneLimits = { task: 1, component: 5, fault: 5, evidence: 6, decision: 5 };
      const cards = new Map();

      const addCard = (node, laneId, options = {}) => {
        if (!node) return null;
        const lane = laneMeta[laneId] || laneMeta.evidence;
        const id = options.id || node.id || `${laneId}:${cards.size}`;
        if (cards.has(id)) {
          const existing = cards.get(id);
          existing.chainIds = [...new Set([...(existing.chainIds || []), ...(options.chainIds || [])])];
          if (options.metaLabel && !existing.metaLabel) existing.metaLabel = options.metaLabel;
          return existing;
        }
        if ((laneBuckets[laneId] || []).length >= (laneLimits[laneId] || 4)) return null;

        const type = options.type || node.type || "Node";
        const card = {
          ...node,
          id,
          type,
          lane: laneId,
          tone: options.tone || this.graphToneForType(type),
          displayLabel: options.displayLabel || this.graphReadableLabel({ ...node, type }, options.maxLabel || 14),
          metaLabel: options.metaLabel || "",
          width: options.width || (laneId === "decision" ? 164 : laneId === "evidence" ? 156 : laneId === "task" ? 144 : 140),
          height: options.height || (laneId === "task" ? 72 : 60),
          x: lane.x,
          y: 260,
          chainIds: options.chainIds || [],
        };
        laneBuckets[laneId].push(card);
        cards.set(id, card);
        return card;
      };

      addCard(
        { id: "current-task", label: this.sessionEquipmentLabel, type: "Task" },
        "task",
        {
          tone: "task",
          displayLabel: this.sessionEquipmentLabel,
          metaLabel: this.sessionComponentCompact,
          width: 150,
          height: 78,
        },
      );

      chains.forEach((chain) => {
        const chainId = chain.id || `${chain.component?.id || "component"}:${chain.fault?.id || "fault"}`;
        addCard(chain.component, "component", {
          tone: "component",
          metaLabel: "结构定位",
          chainIds: [chainId],
          maxLabel: 12,
        });
        addCard(chain.fault, "fault", {
          tone: "fault",
          metaLabel: `${chain.risk}风险 · ${chain.confidence}%`,
          chainIds: [chainId],
          maxLabel: 12,
        });
        chain.evidence.slice(0, 3).forEach((item) => {
          addCard(item, "evidence", {
            tone: item.type === "VisualAsset" ? "visual" : "evidence",
            displayLabel: item.type === "VisualAsset" ? "故障图片证据" : undefined,
            metaLabel: item.evidenceType || this.graphTypeLabel(item.type),
            chainIds: [chainId],
            maxLabel: 15,
          });
        });
        addCard(chain.action, "decision", {
          tone: "process",
          metaLabel: "处置 SOP",
          chainIds: [chainId],
          maxLabel: 13,
        });
        addCard(chain.safety, "decision", {
          tone: "safety",
          metaLabel: "安全闸门",
          chainIds: [chainId],
          maxLabel: 13,
        });
      });

      laneOrder.forEach((laneId) => {
        const items = laneBuckets[laneId] || [];
        const top = laneId === "task" ? 260 : 126;
        const bottom = laneId === "task" ? 260 : 430;
        const gap = items.length <= 1 ? 0 : (bottom - top) / (items.length - 1);
        items.forEach((node, index) => {
          node.y = Math.round(items.length <= 1 ? 260 : top + gap * index);
          if (items.length > 5 && laneId !== "task") node.height = 54;
        });
      });

      return laneOrder.flatMap((laneId) => laneBuckets[laneId] || []);
    },
    graphMapEdges() {
      const nodes = this.graphMapNodes;
      const byId = Object.fromEntries(nodes.map((node) => [node.id, node]));
      const edgeMap = new Map();
      const addEdge = (sourceId, targetId, tone, label) => {
        const source = byId[sourceId];
        const target = byId[targetId];
        if (!source || !target || source.id === target.id) return;
        const id = `${source.id}->${target.id}`;
        if (edgeMap.has(id)) return;
        const x1 = source.x + source.width / 2 - 4;
        const y1 = source.y;
        const x2 = target.x - target.width / 2 + 4;
        const y2 = target.y;
        const curve = Math.max(54, Math.abs(x2 - x1) * 0.46);
        edgeMap.set(id, {
          id,
          source: source.id,
          target: target.id,
          tone,
          label,
          path: `M ${x1} ${y1} C ${x1 + curve} ${y1}, ${x2 - curve} ${y2}, ${x2} ${y2}`,
        });
      };

      this.graphEvidenceChains.slice(0, 6).forEach((chain) => {
        addEdge("current-task", chain.component?.id, "task", "定位到结构部件");
        addEdge(chain.component?.id, chain.fault?.id, "fault", "关联故障模式");
        chain.evidence.slice(0, 3).forEach((item) => {
          addEdge(chain.fault?.id, item.id, item.type === "VisualAsset" ? "visual" : "evidence", item.evidenceType || this.graphTypeLabel(item.type));
        });
        addEdge(chain.fault?.id, chain.action?.id, "process", "生成作业步骤");
        addEdge(chain.fault?.id, chain.safety?.id, "safety", "触发安全闸门");
      });
      return [...edgeMap.values()].slice(0, 28);
    },
    claimReviewPanels() {
      const claim = this.primaryClaimCard || {};
      return [
        {
          key: "evidence",
          label: "证据预算复核",
          status: `${this.claimEvidenceScorePercent}%`,
          summary: "核对 E1-E4 是否支撑当前结论，缺口会反馈给检修任务台。",
          items: this.evidenceBudgetDetails.map((item) => `${item.label}：${item.percent}% / ${item.count} 条`),
        },
        {
          key: "fmea",
          label: "FMEA 风险复核",
          status: this.riskLabel(this.result?.risk_level || "unknown"),
          summary: "复核失效模式、严重度、发生度、可探测度和风险优先数是否符合现场风险。",
          items: this.claimFmeaItems.map((item) => `${item.label}：${item.value}（${item.source}）`),
        },
        {
          key: "safety",
          label: "安全闸门复核",
          status: claim.safety_gate?.state || this.incidentGateState,
          summary: "确认断电、泄压、温度、PPE、工具和验收留痕是否完备。",
          items: this.safetyGateChecklist.map((item) => `${item.display_label}：${item.confirmed ? "已确认" : "待确认"}`),
        },
        {
          key: "human",
          label: "人工修正反馈",
          status: this.feedbackStatus || "待记录",
          summary: "复核后的修改会写入反馈记录，并在当前任务台展示为可追溯修正。",
          items: this.feedbackRecords.slice(0, 3).map((item) => item.notes || item.corrected_answer || "历史修正记录"),
        },
      ];
    },
    activeClaimReviewPanel() {
      return this.claimReviewPanels.find((item) => item.key === this.selectedClaimReviewPanel) || this.claimReviewPanels[0];
    },
    explanationPayload() {
      const type = this.activeExplanation;
      if (type === "confidence") {
        return {
          title: "置信度来源",
          summary: `当前置信度 ${Math.round((this.result?.confidence || 0) * 100)}%，由手册、案例、图谱和视觉证据共同加权，视觉证据不足会拉低最终分。`,
          bars: this.evidenceBudgetDetails.map((item) => ({ label: item.label, value: item.percent, note: `${item.count} 条证据` })),
          items: [
            "手册和案例命中能够确认检修方向。",
            "图谱路径提供部件、故障、SOP、合规之间的可解释关系。",
            "视觉结果只作为辅助证据，需要现场人员确认图片质量和部件位置。",
          ],
        };
      }
      if (type === "risk") {
        return {
          title: "风险判定依据",
          summary: `风险等级为 ${this.riskLabel(this.result?.risk_level || "unknown")}，主要来自 FMEA 评分、安全闸门缺口和高风险拆卸动作。`,
          bars: this.claimFmeaItems.filter((item) => item.key !== "failure_mode").map((item) => ({ label: item.label, value: Number(item.value) || 0, note: item.source })),
          items: this.claimFmeaItems.map((item) => `${item.label}：${item.value}，来源：${item.source}`),
        };
      }
      if (type === "evidence-budget") {
        return {
          title: "证据预算溯源",
          summary: "E1-E4 不只看分数，也要看每类证据的具体命中项和缺口。",
          bars: this.evidenceBudgetDetails.map((item) => ({ label: item.label, value: item.percent, note: item.note })),
          items: this.evidenceBudgetDetails.flatMap((item) => item.items.slice(0, 2).map((evidence) => `${item.label}：${evidence.title}`)),
        };
      }
      if (type === "component-contract") {
        return {
          title: "部件约束来源",
          summary: `当前定位到 ${this.sessionComponentSummary}，来自结构模型部件、视觉线索和作业步骤绑定。`,
          bars: [],
          items: [
            `部件别名：${(this.activeComponentContract?.aliases || []).slice(0, 5).join("、") || "暂无别名"}`,
            `常见故障：${(this.activeComponentContract?.common_faults || []).join("、") || "根据当前证据归纳"}`,
            `安全闸门：${this.componentContractGateDisplayLabels.join("、") || "按作业票安全闸门执行"}`,
          ],
        };
      }
      if (type === "fmea") {
        return {
          title: "FMEA 风险链来源",
          summary: "每个评分项都绑定到故障描述、案例、手册和安全规则，而不是孤立数字。",
          bars: this.claimFmeaItems.filter((item) => item.key !== "failure_mode").map((item) => ({ label: item.label, value: Number(item.value) || 0, note: item.source })),
          items: this.claimFmeaItems.map((item) => `${item.label}：${item.value}，${item.source}`),
        };
      }
      if (type === "safety-gate") {
        return {
          title: "安全闸门状态机",
          summary: this.safetyGateDecisionText,
          bars: this.safetyGateChecklist.map((item) => ({ label: item.display_label, value: item.confirmed ? 100 : 0, note: item.confirmed ? "已确认" : "待确认" })),
          items: this.safetyAuditRows.map((item) => `${item.time} ${item.action}：${item.reason}`),
        };
      }
      if (type === "tri-evidence" || type === "tri-structure" || type === "tri-operation") {
        const labels = {
          "tri-evidence": "证据链解释",
          "tri-structure": "结构链解释",
          "tri-operation": "作业链解释",
        };
        return {
          title: labels[type],
          summary: "三链对齐要求证据、结构和作业票互相指向同一类检修对象。",
          bars: [
            { label: "证据链", value: this.triMroAlignment?.claim?.traceability?.evidence_count || 0, note: "引用数量" },
            { label: "结构链", value: (this.triMroAlignment?.structure_chain?.component_keys || []).length, note: this.sessionComponentSummary },
            { label: "作业链", value: this.triMroAlignment?.claim?.traceability?.operation_step_count || 0, note: "SOP 步骤" },
          ],
          items: [
            `证据链：${this.triMroEvidencePreview}`,
            `结构链：${this.componentSummaryLabel(this.triMroAlignment?.structure_chain?.component_keys || [])}`,
            `作业链：已生成 ${this.operationTicketSteps.length} 个步骤，安全闸门状态 ${this.incidentGateState}`,
          ],
        };
      }
      return null;
    },
    graphLayout() {
      const nodes = this.readableGraph.nodes || [];
      const edges = this.readableGraph.edges || [];
      const columns = {
        Equipment: 110,
        Component: 300,
        VisualAsset: 300,
        Fault: 500,
        SafetyRule: 705,
        Case: 705,
        ManualChunk: 845,
        Process: 845,
      };
      const fallbackX = 500;
      const byColumn = {};
      nodes.forEach((node) => {
        const x = columns[node.type] || fallbackX;
        byColumn[x] = byColumn[x] || [];
        byColumn[x].push(node);
      });
      const positioned = [];
      Object.entries(byColumn).forEach(([xValue, group]) => {
        const x = Number(xValue);
        const sorted = group.sort((a, b) => (GRAPH_TYPE_WEIGHT[b.type] || 0) - (GRAPH_TYPE_WEIGHT[a.type] || 0));
        const gap = Math.min(82, 420 / Math.max(1, sorted.length - 1 || 1));
        const startY = sorted.length === 1 ? 260 : 70;
        sorted.forEach((node, index) => {
          positioned.push({
            ...node,
            x,
            y: sorted.length === 1 ? startY : startY + index * gap,
            r: node.type === "Equipment" ? 25 : node.type === "Fault" ? 18 : 14,
            typeClass: String(node.type || "node").toLowerCase(),
            displayLabel: this.truncateGraphLabel(node.label, node.type),
          });
        });
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
    graphFocusLabel() {
      return this.graphFocusOptions.find((item) => item.id === this.graphFocus)?.label || "设备";
    },
    officialResourceStatus() {
      const resources = this.resourceVerification.resources || [];
      const item = resources.find((resource) => resource.id === "official-motorcycle-engine-manual");
      return item ? item.verify_status : "missing";
    },
    partTreeEquipmentOptions() {
      const equipmentIds = new Set((this.partTreeCandidates.candidates || []).map((item) => item.equipment).filter(Boolean));
      const labels = { bearing: "轴承", motor: "电机", pump: "离心泵", engine: "发动机" };
      return [
        { id: "all", label: "全部" },
        ...["bearing", "motor", "pump", "engine"]
          .filter((id) => equipmentIds.has(id))
          .map((id) => ({ id, label: labels[id] || id })),
      ];
    },
    filteredPartTreeCandidates() {
      const candidates = this.partTreeCandidates.candidates || [];
      if (this.partTreeEquipment === "all") return candidates;
      return candidates.filter((item) => item.equipment === this.partTreeEquipment);
    },
    candidateCadStats() {
      const summary = this.candidateCadSummary || {};
      return [
        { label: "候选资产", value: summary.total || 0 },
        { label: "待审核", value: summary.needs_review || 0 },
        { label: "已批准候选", value: summary.approved_candidate || 0 },
        { label: "已拒绝", value: summary.rejected || 0 },
      ];
    },
    latestCandidateCadAsset() {
      return (this.candidateCadAssets || [])[0] || null;
    },
    selectedCandidateCadAsset() {
      const assets = this.candidateCadAssets || [];
      return assets.find((item) => String(item.id) === String(this.selectedCandidateCadId)) || assets[0] || null;
    },
    candidateCadViewerAsset() {
      const assets = this.candidateCadAssets || [];
      const id = this.candidateCadLightbox.assetId || this.selectedCandidateCadId;
      return assets.find((item) => String(item.id) === String(id)) || this.selectedCandidateCadAsset;
    },
    candidateCadViewerViews() {
      return ["iso", "front", "side", "top"];
    },
    candidateCadViewerLinks() {
      const item = this.candidateCadViewerAsset;
      if (!item) return [];
      return [
        { role: "step", label: "STEP" },
        { role: "stl", label: "STL" },
        { role: "openscad-stl", label: "OpenSCAD STL" },
        { role: "glb", label: "GLB" },
        { role: "freecad-validation", label: "FreeCAD 校验" },
        { role: "blender-report", label: "Blender 报告" },
        { role: "artifact-manifest", label: "Manifest" },
      ];
    },
    candidateCadViewerRotation() {
      const value = Number(this.candidateCadLightbox.rotation || 0);
      return ((value % 360) + 360) % 360;
    },
    candidateCadViewerImageStyle() {
      const rotation = this.candidateCadViewerRotation;
      const scale = rotation % 180 === 0 ? 1 : 0.72;
      return {
        transform: `rotate(${rotation}deg) scale(${scale})`,
      };
    },
    candidateCadViewerGlbUrl() {
      return this.candidateCadViewerAsset ? this.candidateCadFileUrl(this.candidateCadViewerAsset, "glb") : "#";
    },
    cadRuntimeTools() {
      return Object.values(this.cadRuntime?.tools || {});
    },
    partTreeCandidateStats() {
      const summary = this.partTreeCandidates.summary || {};
      return [
        { label: "候选资源", value: summary.total || 0 },
        { label: "验证通过", value: summary.passed || 0 },
        { label: "原生装配树", value: summary.assembly_tree || 0 },
        { label: "多实体/特征树", value: summary.multi_solid_or_feature_tree || 0 },
      ];
    },
    approvedVisualAssetCount() {
      return (this.visualAssets || []).filter((asset) => asset.review_status === "approved").length;
    },
    activeSpatialGuidance() {
      const fallback = {
        highlighted_components: [],
        sop_bindings: [],
        components: this.selectedSpatialModel.components || [],
        safety_gate: { status: "unknown", label: "等待生成导引" },
      };
      const matchesCurrentEquipment = (guidance) => {
        if (!guidance) return false;
        return !guidance.equipment || guidance.equipment === this.query.equipment;
      };
      if (matchesCurrentEquipment(this.spatialGuidance)) return this.spatialGuidance;
      if (matchesCurrentEquipment(this.result?.spatial_guidance)) return this.result.spatial_guidance;
      return fallback;
    },
    generatedCadForEquipment() {
      const eq = this.query.equipment;
      const candidates = this.candidateCadAssets || [];
      return this.currentPhotoCandidateCad || candidates.find((c) => c.equipment === eq && c.status !== "rejected") || null;
    },
    currentPhotoCandidateCad() {
      const visualAssetId = this.query.visual_asset_id;
      if (!visualAssetId) return null;
      const candidates = this.candidateCadAssets || [];
      return candidates.find((c) => String(c.visual_asset_id) === String(visualAssetId) && c.status !== "rejected") || null;
    },
    photoCadViewState() {
      const currentId = this.query.visual_asset_id;
      const generation = this.photoCadGeneration || {};
      const matchesCurrent = String(generation.visual_asset_id || "") === String(currentId || "");
      if (this.uploadingImage) {
        return {
          status: "analyzing",
          title: "正在分析故障照片",
          message: "视觉分析完成后会自动生成照片 CAD 候选资产。",
        };
      }
      if (!currentId) {
        return {
          status: "empty",
          title: "尚未上传故障照片",
          message: "先在左侧上传现场照片；上传完成后系统会自动生成 CAD 候选资产，并在这里展示预览、文件和审核边界。",
        };
      }
      if (generation.status === "generating" && matchesCurrent) {
        return {
          status: "generating",
          title: "正在生成照片 CAD",
          message: generation.message || "正在生成 CAD spec、候选代码和渲染预览。",
        };
      }
      if (this.currentPhotoCandidateCad) {
        return {
          status: "ready",
          title: `照片 CAD 已生成 #${this.currentPhotoCandidateCad.id}`,
          message: "该候选 CAD 由当前照片视觉资产生成，只用于结构理解和人工审核，不用于尺寸测量或安全放行。",
        };
      }
      if (generation.status === "error" && matchesCurrent) {
        return {
          status: "error",
          title: "照片 CAD 生成失败",
          message: generation.error || generation.message || "生成失败，请检查后端 CAD 产物链路。",
        };
      }
      return {
        status: "waiting",
        title: "等待自动生成",
        message: "照片已进入视觉资产库，系统正在等待或准备生成照片 CAD。也可以点击下方按钮重新触发。",
      };
    },
    photoCadResultLinks() {
      const item = this.currentPhotoCandidateCad || this.generatedCadForEquipment;
      if (!item) return [];
      return [
        { role: "glb", label: "GLB" },
        { role: "step", label: "STEP" },
        { role: "stl", label: "STL" },
        { role: "spec", label: "CAD spec" },
        { role: "freecad-validation", label: "FreeCAD 校验" },
      ];
    },
    generatedCadModel() {
      const cad = this.generatedCadForEquipment;
      if (!cad) return null;
      const obs = cad.observation || {};
      const spec = cad.editable_spec || cad.cad_spec || {};
      const defects = obs.defect_labels || [];
      const componentCandidates = obs.component_candidates || [];
      const componentMap = new Map();
      (spec.components || []).forEach((item) => {
        const key = item.component_key || item.key;
        if (!key) return;
        componentMap.set(key, {
          component_key: key,
          label: item.label || key.split(".").pop(),
          role: item.role || "candidate_geometry_anchor",
          source: item.source || "照片生成 CAD",
        });
      });
      (spec.component_keys || []).forEach((key) => {
        if (!key || componentMap.has(key)) return;
        componentMap.set(key, {
          component_key: key,
          label: key.split(".").pop(),
          role: "candidate_geometry_anchor",
          source: "照片生成 CAD",
        });
      });
      const highlighted = componentCandidates.map((item) => ({
        component_key: `${cad.equipment}.${(item.id || item.label || "unknown").toLowerCase().replace(/[\s\/]+/g, "_")}`,
        label: item.label || item.id || "未知部件",
        confidence: item.confidence || 0.5,
        tone: defects.some((d) => d.confidence > 0.7) ? "danger" : "warning",
        reason: defects.map((d) => d.label).join("、") || "照片识别标注",
        safety_tags: obs.risk_hints || [],
      }));
      return {
        id: `cad-candidate-${cad.id}`,
        equipment: cad.equipment,
        title: `照片生成 #${cad.id} · ${obs.caption || cad.equipment}`,
        source_type: "candidate_cad",
        viewer_mode: "local_glb",
        mesh_path: `data/cad_candidates/candidate_${String(cad.id).padStart(4, "0")}_${cad.equipment}/candidate.glb`,
        processed_mesh_url: `/api/cad/candidates/${cad.id}/files/glb`,
        asset_status: cad.status,
        license: { id: "generated", label: "照片生成（实验性）" },
        components: Array.from(componentMap.values()),
        cad_bridge: { viewer_mode: "local_glb", binding_mode: "generated" },
        node_bindings: { binding_mode: "generated" },
        highlighted_components: highlighted,
        defect_labels: defects,
        observation_caption: obs.caption || "",
      };
    },
    spatialCalibrationComponents() {
      const components = this.spatialModelSource === "generated"
        ? this.generatedCadModel?.components || []
        : this.activeSpatialGuidance.components?.length
          ? this.activeSpatialGuidance.components
          : this.selectedSpatialModel.components || [];
      const seen = new Set();
      return components
        .map((item) => ({
          component_key: item.component_key || item.key,
          label: item.label || item.component_key || item.key,
          source: item.source || item.role || "",
        }))
        .filter((item) => {
          if (!item.component_key || seen.has(item.component_key)) return false;
          seen.add(item.component_key);
          return true;
        });
    },
    spatialStepGroups() {
      const bindings = this.activeSpatialGuidance.sop_bindings || [];
      const groups = [];
      const byKey = new Map();
      bindings.forEach((binding) => {
        const componentKey = binding.component_key || "unbound";
        if (!byKey.has(componentKey)) {
          const group = {
            component_key: componentKey,
            label: componentKey === "unbound" ? "未绑定部件" : this.spatialComponentLabel(componentKey),
            steps: [],
            phases: [],
            risk_controls: [],
          };
          byKey.set(componentKey, group);
          groups.push(group);
        }
        const group = byKey.get(componentKey);
        const stepIndex = Number(binding.step_index || 0);
        if (stepIndex && !group.steps.includes(stepIndex)) group.steps.push(stepIndex);
        const phase = binding.phase || "作业步骤";
        if (phase && !group.phases.includes(phase)) group.phases.push(phase);
        const riskControl = binding.risk_control || "";
        if (riskControl && !group.risk_controls.includes(riskControl)) group.risk_controls.push(riskControl);
      });
      return groups.map((group) => {
        const steps = group.steps.sort((a, b) => a - b);
        return {
          ...group,
          step_label: this.compactStepLabel(steps),
          phase_label: this.compactListLabel(group.phases),
          risk_label: this.compactListLabel(group.risk_controls),
          step_count: steps.length,
        };
      });
    },
    spatialGateStatus() {
      return this.activeSpatialGuidance.safety_gate?.status || "unknown";
    },
    spatialGateLabel() {
      return this.activeSpatialGuidance.safety_gate?.label || "等待生成导引";
    },
    incidentMissingItems() {
      if (!this.hasActiveMaintenanceResult) return [];
      const claimMissing = this.primaryClaimCard?.safety_gate?.missing_items || [];
      const workflowMissing = this.workflowState?.safety_gate?.blocking_items || [];
      const triMissing = this.triMroAlignment?.safety_gate?.missing_items || [];
      const combined = [...claimMissing, ...workflowMissing, ...triMissing].filter(Boolean);
      return combined.length ? [...new Set(combined)] : ["未确认断电挂牌", "未确认泄压", "未确认 PPE"];
    },
    incidentGateChips() {
      const gateReady = this.safetyGateResolved || String(this.incidentGateState || "").toLowerCase().includes("ready");
      if (gateReady) {
        return this.safetyGateChecklist.slice(0, 4).map((item) => ({
          label: `${item.display_label || item.label}已确认`,
          confirmed: true,
        }));
      }
      return this.incidentMissingItems.slice(0, 4).map((label) => ({
        label,
        confirmed: false,
      }));
    },
    incidentGateState() {
      if (!this.hasActiveMaintenanceResult) return "未开始";
      if (this.safetyGateResolved) return "READY";
      const raw = this.primaryClaimCard?.safety_gate?.state
        || this.workflowState?.safety_gate?.status
        || this.triMroAlignment?.safety_gate?.status
        || "BLOCKED";
      return String(raw || "BLOCKED").toUpperCase();
    },
    incidentGateClass() {
      const state = this.incidentGateState.toLowerCase();
      if (state.includes("未开始") || state.includes("not_started")) return "gate-neutral";
      if (state.includes("ready") || state.includes("allow")) return "gate-ready";
      if (state.includes("review") || state.includes("wait") || state.includes("confirm")) return "gate-warning";
      return "gate-blocked";
    },
    incidentCoreValue() {
      return "系统没有急着回答“怎么修”，而是先判断“现在能不能修”。";
    },
    safetyGateChecklist() {
      const fallback = ["断电挂牌", "泄压确认", "温度安全", "PPE确认", "工具确认"];
      const required = [
        ...(this.primaryClaimCard?.safety_gate?.required_gates || []),
        ...(this.componentContractGateLabels || []),
      ];
      const labels = [];
      const seen = new Set();
      [...required, ...fallback].filter(Boolean).forEach((label) => {
        const display = this.formatGateLabel(label);
        const key = this.safetyKey(display);
        if (seen.has(key)) return;
        seen.add(key);
        labels.push({ label, display, key });
      });
      const missingText = this.incidentMissingItems.join(" ");
      return labels.map(({ label, display, key }) => {
        const isMissing = missingText.includes(label)
          || missingText.includes(display)
          || missingText.includes(display.replace("确认", ""))
          || missingText.includes(display.replace("挂牌", ""));
        return {
          key,
          label,
          display_label: display,
          confirmed: Boolean(this.safetyConfirmations[key]) || (!!this.result && !isMissing),
          missing: isMissing && !this.safetyConfirmations[key],
        };
      });
    },
    safetyGateResolved() {
      const checklist = this.safetyGateChecklist;
      return checklist.length > 0 && checklist.every((item) => item.confirmed);
    },
    safetyGateDecisionText() {
      if (!this.hasActiveMaintenanceResult) return "请先在检修任务台生成检修方案，再进入安全闸门确认。";
      if (this.safetyGateResolved) return "安全前置条件已确认，可进入受控检修步骤。";
      return this.primaryClaimCard?.safety_gate?.decision
        || this.triMroAlignment?.safety_gate?.decision
        || "禁止进入拆卸步骤，必须先完成安全闸门确认。";
    },
    safetyAuditRows() {
      const audit = this.primaryClaimCard?.safety_gate?.audit_trail || [];
      const checklist = this.safetyGateChecklist;
      const confirmations = checklist
        .filter((item) => item.confirmed)
        .map((item, index) => ({
          time: `14:${String(22 + index).padStart(2, "0")}`,
          action: `确认 ${item.display_label || item.label}`,
          reason: this.safetyConfirmations[item.key] ? "现场人工确认并写入本地审计记录" : "已由方案证据预确认，等待现场复核留痕",
        }));
      if (audit.length && !this.safetyGateResolved) {
        return audit.map((item, index) => ({
          time: item.time || `T+${index}`,
          action: item.action || "系统记录",
          reason: item.reason || item.detail || "安全状态变化",
        }));
      }
      const missing = checklist.filter((item) => !item.confirmed).map((item) => item.display_label || item.label);
      const base = this.safetyGateResolved
        ? [
            { time: "14:20", action: "生成受控作业票", reason: "高风险步骤已绑定安全闸门和验收标准" },
            { time: "14:21", action: "安全闸门放行", reason: `已确认 ${checklist.length}/${checklist.length} 项前置条件` },
          ]
        : [
            { time: "14:20", action: "系统阻断拆卸请求", reason: missing.length ? `缺少 ${missing.join("、")} 确认` : "等待现场确认" },
            { time: "14:21", action: "生成作业票", reason: "高风险步骤进入等待安全确认" },
          ];
      return [...base, ...confirmations];
    },
    safetyListSummaryCards() {
      const steps = this.operationTicketSteps;
      const highRisk = steps.filter((step) => step.risk === "high").length;
      const blocked = steps.filter((step) => step.state === "BLOCKED").length;
      const confirmed = this.safetyGateChecklist.filter((item) => item.confirmed).length;
      return [
        {
          label: "作业步骤",
          value: steps.length,
          note: "从 SOP 自动生成",
          tone: "summary-neutral",
        },
        {
          label: "高风险步骤",
          value: highRisk,
          note: "需安全闸门确认",
          tone: highRisk ? "summary-danger" : "summary-ok",
        },
        {
          label: "当前阻断",
          value: blocked,
          note: blocked ? "进入执行页处理" : "暂无阻断步骤",
          tone: blocked ? "summary-danger" : "summary-ok",
        },
        {
          label: "闸门确认",
          value: `${confirmed}/${this.safetyGateChecklist.length}`,
          note: "断电、泄压、PPE 等",
          tone: this.safetyGateResolved ? "summary-ok" : "summary-warning",
        },
      ];
    },
    operationTicketSteps() {
      const sourceSteps = this.result?.sop_steps?.length
        ? this.result.sop_steps
        : [
            "作业前安全确认：断电挂牌、泄压、温度安全、PPE 与工具确认。",
            "清理机械密封端泄漏区域，拍照记录污染范围。",
            "在安全闸门通过后拆卸机械密封端盖。",
            "检查密封端面、密封圈、泵轴跳动和轴承端状态。",
            "更换或调整密封件，按扭矩要求回装。",
            "低速试运行，确认无持续泄漏、无异常振动和温升。",
            "填写验收结果并生成案例草稿。",
          ];
      const componentKey = (this.workflowState.selected_component_keys || [])[0] || "pump.mechanical_seal";
      const component = this.componentDisplayName(componentKey);
      return sourceSteps.map((step, index) => {
        const risk = /拆卸|试运行|断电|泄压|高温|吊装|打开/.test(step) || index === 0 ? "high" : /检查|更换|回装/.test(step) ? "medium" : "low";
        const blocked = risk === "high" && !this.safetyGateResolved;
        return {
          id: `sop_${index + 1}`,
          index: index + 1,
          text: step,
          risk,
          component,
          state: blocked ? "BLOCKED" : risk === "high" ? "READY" : "READY",
        };
      });
    },
    workOrderTools() {
      const tools = this.result?.tools_and_parts || [];
      return tools.length ? tools : ["扳手", "密封件", "清洁布", "护目镜", "防护手套", "测温工具", "泄压确认流程"];
    },
    acceptanceCriteria() {
      return [
        "机械密封端无持续滴漏或处于允许范围内",
        "泵体复运后无异常振动、异响和快速温升",
        "安全确认、拆检照片、处理措施和复测结果记录完整",
        "需要复核的 CAD 语义热点已由人工确认或标记限制",
      ];
    },
  },
  async mounted() {
    this.applyInitialRouteFromUrl();
    window.addEventListener("keydown", this.handleGlobalKeydown);
    await this.refreshAll();
  },
  unmounted() {
    window.removeEventListener("keydown", this.handleGlobalKeydown);
    this.stopAgentProgress(false);
    this.disposeCandidateCadGlbViewer();
  },
  updated() {
    this.paintIcons();
  },
  watch: {
    activeTab(value, previous) {
      const wasSpatial = previous === "spatial" || previous?.startsWith("spatial_");
      const isSpatial = value === "spatial" || value?.startsWith("spatial_");
      if (wasSpatial && !isSpatial && this.spatialViewer?.dispose) {
        this.spatialViewer.dispose();
        this.spatialViewer = null;
      }
      if (isSpatial && !wasSpatial) {
        this.spatialSection = false;
        this.loadSpatialModels().finally(() => this.renderSpatialViewer());
      }
    },
  },
  methods: {
    applyProfessionalSpatialDefaults() {
      this.expandedNavGroup = "overview";
      this.applyEquipmentPreset("pump", { clearVisual: false, clearResult: false });
      this.spatialGuidance = {
        highlighted_components: [],
        sop_bindings: [],
        scene_state: { timeline: [] },
        components: [],
        safety_gate: { status: "unknown", label: "等待生成导引" },
      };
      this.updateCurrentSession();
    },
    equipmentPreset(equipment) {
      return EQUIPMENT_QUERY_PRESETS[equipment] || EQUIPMENT_QUERY_PRESETS.pump;
    },
    resetDraftSession() {
      this.result = null;
      this.safetyConfirmations = {};
      this.query.model = "";
      this.query.text = "";
      this.query.image_caption = "";
      this.query.visual_asset_id = null;
      this.uploadedImage = {};
      this.uploadStatus = "";
      this.uploadingImage = false;
      this.currentSession = {
        task_id: "draft",
        equipment: "",
        model: "",
        query_text: "",
        visual_asset_id: null,
        selected_component_keys: [],
        selected_model_component_keys: [],
        tri_mro_alignment: null,
        claim_cards: [],
        primary_claim_card: null,
        workflow_state: {
          task_id: "draft",
          equipment: "",
          model: "",
          selected_component_keys: [],
          selected_model_component_keys: [],
          stages: [],
          safety_gate: { status: "unknown", label: "等待生成方案", blocking_items: [] },
        },
        visual_analysis: null,
        updated_at: new Date().toLocaleTimeString(),
      };
    },
    applyEquipmentPreset(equipment, options = {}) {
      const preset = this.equipmentPreset(equipment);
      const clearVisual = options.clearVisual !== false;
      const clearResult = options.clearResult !== false;
      this.query.equipment = equipment;
      this.query.model = preset.model;
      this.query.maintenance_level = preset.maintenance_level;
      this.query.text = preset.text;
      this.query.top_k = this.query.top_k || 6;
      if (clearVisual) {
        this.query.image_caption = "";
        this.query.visual_asset_id = null;
        this.uploadedImage = {};
        this.uploadStatus = "";
        this.uploadingImage = false;
      }
      if (clearResult) {
        this.result = null;
        this.safetyConfirmations = {};
        this.stopAgentProgress(false);
      }
      this.currentSession = {
        task_id: "draft",
        equipment,
        model: preset.model,
        query_text: preset.text,
        visual_asset_id: this.query.visual_asset_id,
        selected_component_keys: [],
        selected_model_component_keys: [],
        tri_mro_alignment: null,
        claim_cards: [],
        primary_claim_card: null,
        workflow_state: {
          task_id: "draft",
          equipment,
          model: preset.model,
          selected_component_keys: [],
          selected_model_component_keys: [],
          stages: [],
          safety_gate: { status: "unknown", label: "等待生成方案", blocking_items: [] },
        },
        visual_analysis: null,
        updated_at: new Date().toLocaleTimeString(),
      };
      this.graphFocus = equipment;
      this.focusedSpatialComponentKey = "";
      this.spatialCalibrationComponentKey = "";
      if (this.spatialGuidance?.equipment && this.spatialGuidance.equipment !== equipment) {
        this.spatialGuidance = null;
      }
    },
    changeDiagnosisEquipment() {
      if (!this.query.equipment) {
        this.resetDraftSession();
        this.paintIcons();
        return;
      }
      this.applyEquipmentPreset(this.query.equipment);
      this.paintIcons();
    },
    applyInitialRouteFromUrl() {
      const params = new URLSearchParams(window.location.search || "");
      const tab = params.get("tab");
      const graphFocus = params.get("graphFocus");
      if (this.allNavIds.includes(tab)) this.activeTab = tab;
      if (this.graphFocusOptions.some((item) => item.id === graphFocus)) this.graphFocus = graphFocus;
    },
    startAgentProgress() {
      this.stopAgentProgress(false);
      this.agentProgressIndex = 0;
      this.agentProgressTimer = window.setInterval(() => {
        const total = this.agentProgressBlueprint.length || 1;
        if (this.agentProgressIndex < total - 1) {
          this.agentProgressIndex++;
        }
      }, 900);
    },
    stopAgentProgress(markComplete = true) {
      if (this.agentProgressTimer) {
        window.clearInterval(this.agentProgressTimer);
        this.agentProgressTimer = null;
      }
      if (markComplete && this.agentProgressBlueprint.length) {
        this.agentProgressIndex = this.agentProgressBlueprint.length - 1;
      }
    },
    switchTab(tab) {
      if (!this.allNavIds.includes(tab)) return;
      this.activeTab = tab;
      if (tab !== "cases" && !tab.startsWith("cases")) this.lastTaskTab = tab;
      for (const g of this.navGroups) {
        if (g.id === tab || g.children.some((c) => c.id === tab)) {
          this.expandedNavGroup = g.id;
          break;
        }
      }
      this.paintIcons();
    },
    toggleNavGroup(groupId) {
      this.expandedNavGroup = this.expandedNavGroup === groupId ? "" : groupId;
      this.paintIcons();
    },
    setGraphFocus(id) {
      this.graphFocus = id;
      this.selectedGraphNodeId = "";
    },
    toggleGraphLayer(id) {
      this.graphLayers[id] = !this.graphLayers[id];
      this.selectedGraphNodeId = "";
    },
    selectGraphNode(id) {
      this.selectedGraphNodeId = id;
      this.paintIcons();
    },
    clearGraphNode() {
      this.selectedGraphNodeId = "";
      this.paintIcons();
    },
    graphTypeLabel(type) {
      return {
        Task: "任务",
        Equipment: "设备",
        Component: "部件",
        Fault: "故障",
        Cause: "原因",
        Process: "SOP",
        SafetyRule: "合规规则",
        Case: "案例",
        ManualChunk: "手册证据",
        VisualAsset: "视觉证据",
      }[type] || type || "节点";
    },
    graphToneForType(type) {
      return {
        Task: "task",
        Equipment: "task",
        Component: "component",
        Fault: "fault",
        Cause: "cause",
        Process: "process",
        SafetyRule: "safety",
        Case: "evidence",
        ManualChunk: "evidence",
        VisualAsset: "visual",
      }[type] || "evidence";
    },
    graphReadableLabel(node, maxLength = 14) {
      const type = typeof node === "object" ? node.type : "";
      const raw = String(typeof node === "object" ? node.label || "" : node || "").trim();
      const shouldMapComponent = type === "Component" || /^(pump|motor|bearing|engine)[.:]/i.test(raw);
      let label = shouldMapComponent ? this.componentDisplayName(raw) : raw;
      label = label
        .replace(/\.(jpg|jpeg|png|webp)$/i, "")
        .replace(/[_-]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
      if (!label) label = this.graphTypeLabel(type);
      return label.length > maxLength ? `${label.slice(0, maxLength)}...` : label;
    },
    inferGraphRisk(label) {
      const text = String(label || "");
      if (/泄漏|绝缘|压缩|断裂|汽蚀/.test(text)) return "高";
      if (/过热|振动|剥落|磨损|油污|异响/.test(text)) return "中";
      return "低";
    },
    truncateGraphLabel(label, type) {
      const raw = String(label || "");
      const maxLength = type === "ManualChunk" ? 18 : type === "SafetyRule" ? 12 : 10;
      return raw.length > maxLength ? `${raw.slice(0, maxLength)}…` : raw;
    },
    componentDisplayName(componentKey) {
      const raw = String(componentKey || "").trim();
      if (!raw) return "待定位部件";
      const staticMap = {
        "pump.mechanical_seal": "泵头机械密封区",
        "pump.inlet_outlet": "进出口管口",
        "pump.shaft": "泵轴与轴端",
        "pump.impeller": "叶轮",
        "pump.bearing": "泵轴承座",
        "motor.bearing": "电机轴承端",
        "motor.winding": "电机绕组",
        "motor.terminal_box": "接线盒",
        "bearing.inner_ring": "轴承内圈",
        "bearing.outer_ring": "轴承外圈",
        "bearing.rolling_element": "滚动体",
        "engine.cooling": "冷却系统",
        "engine.fuel": "燃油供给",
      };
      if (staticMap[raw]) return staticMap[raw];
      const components = [
        ...(this.activeSpatialGuidance?.components || []),
        ...(this.selectedSpatialModel?.components || []),
        ...((this.activeSpatialGuidance?.highlighted_components || []).map((item) => ({ component_key: item.component_key, label: item.label }))),
      ];
      const matched = components.find((item) => item.component_key === raw);
      if (matched?.label) return matched.label;
      return raw
        .replace(/^pump\./, "泵 ")
        .replace(/^motor\./, "电机 ")
        .replace(/^bearing\./, "轴承 ")
        .replace(/^engine\./, "发动机 ")
        .replace(/mechanical_seal/g, "机械密封")
        .replace(/inlet_outlet/g, "进出口")
        .replace(/shaft/g, "轴")
        .replace(/_/g, " ");
    },
    componentSummaryLabel(keys, limit = 0) {
      const list = (Array.isArray(keys) ? keys : [keys]).filter(Boolean).map((key) => this.componentDisplayName(key));
      if (!list.length) return "待定位部件";
      const visible = limit ? list.slice(0, limit) : list;
      const suffix = limit && list.length > limit ? `等 ${list.length} 处` : "";
      return [visible.join(" / "), suffix].filter(Boolean).join(" ");
    },
    openExplanation(type) {
      this.activeExplanation = this.activeExplanation === type ? "" : type;
      nextTick(() => this.paintIcons());
    },
    closeExplanation() {
      this.activeExplanation = "";
    },
    selectClaimReviewPanel(key) {
      this.selectedClaimReviewPanel = key;
      nextTick(() => this.paintIcons());
    },
    async applyHumanReviewFeedback() {
      if (!this.result) return;
      const panel = this.activeClaimReviewPanel;
      const suffix = [
        "",
        "人工复核反馈：",
        `${panel.label} - ${panel.summary}`,
        "系统已将该复核意见写入反馈记录；工作台会在当前任务中将人工意见作为后续答案修正依据。",
      ].join("\n");
      if (!this.feedbackForm.corrected_answer.includes(panel.summary)) {
        this.feedbackForm.corrected_answer = `${this.feedbackForm.corrected_answer || this.composeOriginalAnswer()}${suffix}`;
      }
      this.feedbackForm.notes = `${panel.label} 已复核：影响证据预算、风险等级和安全闸门解释。`;
      await this.submitFeedback();
      this.feedbackStatus = "已反馈给检修任务台，当前方案将按人工复核意见重新考虑。";
      this.switchTab("diagnosis");
    },
    visualAssetImageUrl(asset) {
      const id = asset?.id || asset;
      return id ? `/api/visual-assets/${encodeURIComponent(id)}/file` : "";
    },
    paintIcons() {
      nextTick(() => {
        if (window.lucide) window.lucide.createIcons();
      });
    },
    escapeHtml(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    },
    async api(path, options = {}) {
      const apiBase = (window.A1_API_BASE_URL || "").replace(/\/$/, "");
      const res = await fetch(`${apiBase}${path}`, options);
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    updateCurrentSession(result = null) {
      const sourceResult = result || this.result || {};
      const workflow = sourceResult.workflow_state || this.currentSession.workflow_state || {
        task_id: "draft",
        equipment: this.query.equipment,
        model: this.query.model,
        selected_component_keys: [],
        selected_model_component_keys: [],
        stages: [],
        safety_gate: { status: "unknown", label: "等待生成方案", blocking_items: [] },
      };
      this.currentSession = {
        task_id: workflow.task_id || "draft",
        equipment: workflow.equipment || this.query.equipment,
        model: workflow.model || this.query.model,
        query_text: this.query.text,
        visual_asset_id: this.query.visual_asset_id,
        selected_component_keys: workflow.selected_component_keys || [],
        selected_model_component_keys: workflow.selected_model_component_keys || [],
        workflow_state: workflow,
        tri_mro_alignment: sourceResult.tri_mro_alignment || this.currentSession.tri_mro_alignment || null,
        claim_cards: sourceResult.claim_cards || this.currentSession.claim_cards || [],
        primary_claim_card: sourceResult.primary_claim_card || this.currentSession.primary_claim_card || null,
        visual_analysis: sourceResult.visual_analysis || this.uploadedImage.visual_analysis || null,
        result: sourceResult,
        updated_at: new Date().toLocaleTimeString(),
      };
      if (workflow.equipment && this.graphFocusOptions.some((item) => item.id === workflow.equipment)) {
        this.graphFocus = workflow.equipment;
      }
      const activeComponent = sourceResult.spatial_guidance?.scene_state?.active_component_key
        || workflow.selected_model_component_keys?.[0]
        || "";
      if (activeComponent) this.focusedSpatialComponentKey = activeComponent;
    },
    prefillCaseFromCurrentSession() {
      this.lastTaskTab = this.activeTab === "cases" ? this.lastTaskTab : this.activeTab || "diagnosis";
      const workflow = this.workflowState;
      const result = this.result || {};
      const claim = this.primaryClaimCard || {};
      const fmea = claim.fmea_risk_chain || {};
      const components = workflow.selected_component_keys || [];
      this.caseForm = {
        title: `当前任务沉淀：${this.sessionEquipmentLabel} ${components[0] ? this.componentDisplayName(components[0]) : fmea.failure_mode || "待定位部件"}`,
        equipment: workflow.equipment || this.query.equipment,
        model: workflow.model || this.query.model,
        symptoms: this.query.text,
        fault_type: this.componentSummaryLabel(components) || (result.possible_causes || [])[0] || "待确认故障",
        cause: [
          (result.possible_causes || []).join("；") || "需结合手册证据和现场复核确认原因。",
          fmea.failure_mode ? `FMEA：${fmea.failure_mode}，风险优先数 ${fmea.risk_priority || 0}。` : "",
          claim.evidence_budget?.decision ? `证据预算：${claim.evidence_budget.decision}，分数 ${Math.round((claim.evidence_budget.score || 0) * 100)}%。` : "",
        ].filter(Boolean).join("\n"),
        actions: [
          ...(result.sop_steps || []),
          ...(claim.safety_gate?.missing_items?.length ? [`安全闸门缺口：${claim.safety_gate.missing_items.join("、")}`] : []),
        ].join("\n"),
        parts: (result.tools_and_parts || []).join(", "),
        risk_level: result.risk_level || "medium",
      };
      this.activeTab = "cases";
      this.paintIcons();
    },
    returnToDiagnosisResult() {
      this.activeTab = "diagnosis";
      this.lastTaskTab = "diagnosis";
      nextTick(() => {
        window.scrollTo({ top: 0, behavior: "smooth" });
        this.paintIcons();
      });
    },
    goToSpatialWorkbench() {
      this.activeTab = "spatial";
      this.loadSpatialModels().finally(() => this.renderSpatialViewer());
    },
    goToSafetyWorkbench() {
      this.activeTab = "safety";
      this.paintIcons();
    },
    formatGateLabel(label) {
      const raw = String(label || "");
      const normalized = raw.toLowerCase();
      const map = {
        power_locked_out: "断电挂牌",
        zero_voltage_verified: "零电压确认",
        pressure_released: "泄压确认",
        temperature_safe: "温度安全",
        ppe_confirmed: "PPE确认",
        tool_checked: "工具确认",
        stopped_and_locked: "停机闭锁",
        residual_energy_released: "残余能量释放",
      };
      if (map[normalized]) return map[normalized];
      return raw
        .replace(/^未确认/, "")
        .replace(/_/g, " ")
        .replace(/\bpower locked out\b/i, "断电挂牌")
        .replace(/\bzero voltage verified\b/i, "零电压确认")
        .replace(/\bpressure released\b/i, "泄压确认")
        .replace(/\btemperature safe\b/i, "温度安全")
        .replace(/\bppe confirmed\b/i, "PPE确认")
        .replace(/\btool checked\b/i, "工具确认");
    },
    safetyKey(label) {
      return String(label || "")
        .replace(/^未确认/, "")
        .replace(/\s+/g, "_")
        .replace(/[^\u4e00-\u9fa5A-Za-z0-9_]/g, "_");
    },
    confirmSafetyGate(label) {
      const key = this.safetyKey(label);
      this.safetyConfirmations = { ...this.safetyConfirmations, [key]: true };
      this.paintIcons();
    },
    resetSafetyGateConfirmations() {
      this.safetyConfirmations = {};
      this.paintIcons();
    },
    async changeSpatialEquipment() {
      const equipment = this.query.equipment;
      if (!equipment) {
        this.resetDraftSession();
        this.selectedSpatialModelId = "";
        this.selectedSpatialModel = { components: [] };
        this.renderSpatialViewer();
        this.paintIcons();
        return;
      }
      this.applyEquipmentPreset(equipment);
      this.selectedSpatialModelId = "";
      this.selectedSpatialModel = { components: [] };
      this.focusedSpatialComponentKey = "";
      this.spatialCalibrationComponentKey = "";
      await this.loadSpatialModels();
      this.renderSpatialViewer();
      this.paintIcons();
    },
    async refreshAll() {
      try {
        const [health, devices] = await Promise.all([
          this.api("/api/health"),
          this.api("/api/devices"),
        ]);
        this.health = health;
        this.devices = devices.devices || [];
        this.levels = devices.levels || [];
        this.paintIcons();

        const spatialModelsRequest = this.query.equipment
          ? this.api(`/api/3d/models?equipment=${encodeURIComponent(this.query.equipment)}`)
          : Promise.resolve({ models: [] });
        const [providers, routes, graph, graphStatus, visualAssets, metrics, reviewStatus, imageEvalStatus, resourceVerification, pending, feedback, spatialModels, candidateCadAssets, cadRuntime, partTreeCandidates] = await Promise.all([
          this.api("/api/providers"),
          this.api("/api/agent-routing"),
          this.api("/api/knowledge-graph"),
          this.api("/api/graph/status"),
          this.api("/api/visual-assets"),
          this.api("/api/metrics"),
          this.api("/api/review-status"),
          this.api("/api/image-eval/status"),
          this.api("/api/resources/verification"),
          this.api("/api/cases?status=pending"),
          this.api("/api/feedback"),
          spatialModelsRequest,
          this.api("/api/cad/candidates"),
          this.api("/api/cad/runtime"),
          this.api("/api/3d/part-tree-candidates"),
        ]);
        this.providers = providers.providers;
        this.agentRoutes = routes.routes;
        this.graph = graph;
        this.graphStatus = graphStatus;
        this.visualAssets = visualAssets.assets || [];
        this.metrics = metrics;
        this.reviewStatus = reviewStatus;
        this.imageEvalStatus = imageEvalStatus;
        this.resourceVerification = resourceVerification;
        this.pendingCases = pending.cases;
        this.feedbackRecords = feedback.feedback;
        this.spatialModels = spatialModels.models || [];
        this.candidateCadAssets = candidateCadAssets.candidates || [];
        this.candidateCadSummary = candidateCadAssets.summary || {};
        this.cadRuntime = cadRuntime || { tools: {}, recommended_mode: "unknown" };
        this.partTreeCandidates = partTreeCandidates;
        if (!this.selectedCandidateCadId && this.candidateCadAssets.length) {
          this.selectCandidateCad(this.candidateCadAssets[0]);
        } else if (this.selectedCandidateCadId) {
          const selected = this.selectedCandidateCadAsset;
          if (selected && !this.candidateCadSpecDraft) this.selectCandidateCad(selected);
        }
        if (!this.selectedSpatialModelId && this.spatialModels.length) {
          this.selectedSpatialModelId = this.spatialModels[0].id;
          await this.loadSpatialModelDetail();
        }
      } catch (error) {
        this.queryError = `初始化数据失败：${error.message || error}`;
      } finally {
        this.paintIcons();
      }
    },
    async uploadImageFromFile(file) {
      if (!file) return;
      if (file.type && !file.type.startsWith("image/")) {
        this.queryError = "请选择图片文件。";
        this.uploadStatus = "当前文件不是图片，未上传。";
        return;
      }
      const form = new FormData();
      form.append("file", file);
      this.queryError = "";
      this.uploadStatus = "图片已选择，正在上传并进行视觉分析...";
      this.uploadingImage = true;
      this.uploadedImage = { filename: file.name, pending: true };
      try {
        const uploaded = await this.api("/api/upload-image", { method: "POST", body: form });
        this.applyUploadedImage(uploaded);
      } catch (error) {
        this.queryError = `图片上传或视觉分析失败：${error.message || error}`;
        this.uploadStatus = "图片上传失败，请检查文件格式、大小或后端服务状态。";
      } finally {
        this.uploadingImage = false;
        this.paintIcons();
      }
    },
    async uploadImage(event) {
      const file = event.target.files?.[0];
      await this.uploadImageFromFile(file);
      if (event.target) event.target.value = "";
    },
    async uploadImageDrop(event) {
      const files = Array.from(event.dataTransfer?.files || []);
      const file = files.find((item) => item.type?.startsWith("image/")) || files[0];
      await this.uploadImageFromFile(file);
      if (event.dataTransfer) event.dataTransfer.clearData();
    },
    applyUploadedImage(uploaded) {
      this.uploadedImage = uploaded;
      this.query.image_caption = uploaded.caption;
      this.query.visual_asset_id = uploaded.visual_asset_id || null;
      this.uploadStatus = uploaded.visual_analysis?.ok === false
        ? "图片已导入。远程视觉模型未及时返回，当前使用本地视觉规则结果参与检索。"
        : "图片已导入，视觉分析结果和证据图谱已更新。";
      this.updateCurrentSession();
      this.autoGenerateCadFromUploadedImage(uploaded);
    },
    async autoGenerateCadFromUploadedImage(uploaded) {
      const visualAssetId = uploaded?.visual_asset_id || this.query.visual_asset_id;
      if (!visualAssetId) return;
      const existing = this.candidateCadAssets.find((item) => String(item.visual_asset_id) === String(visualAssetId) && item.status !== "rejected");
      if (existing) {
        this.photoCadGeneration = {
          status: "ready",
          visual_asset_id: visualAssetId,
          candidate_id: existing.id,
          message: `当前照片已有关联候选 CAD #${existing.id}。`,
          error: "",
        };
        this.selectedCandidateCadId = existing.id;
        return;
      }
      if (
        this.photoCadGeneration.status === "generating"
        && String(this.photoCadGeneration.visual_asset_id) === String(visualAssetId)
      ) {
        return;
      }
      this.photoCadGeneration = {
        status: "generating",
        visual_asset_id: visualAssetId,
        candidate_id: "",
        message: "视觉分析完成，正在生成 CAD spec、候选代码和渲染预览...",
        error: "",
      };
      try {
        const response = await this.api("/api/cad/candidates/from-visual", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            visual_asset_id: visualAssetId,
            equipment: this.query.equipment,
            model: this.query.model,
            generator: "cadquery_openscad",
          }),
        });
        const candidate = response.candidate;
        this.candidateCadAssets = [candidate, ...this.candidateCadAssets.filter((item) => item.id !== candidate.id)];
        this.candidateCadSummary = { ...this.candidateCadSummary, total: Math.max(this.candidateCadSummary.total || 0, this.candidateCadAssets.length) };
        if (String(this.query.visual_asset_id || "") === String(visualAssetId)) {
          this.selectedCandidateCadId = candidate.id;
          this.photoCadGeneration = {
            status: "ready",
            visual_asset_id: visualAssetId,
            candidate_id: candidate.id,
            message: `照片 CAD #${candidate.id} 已生成，等待人工机械审核。`,
            error: "",
          };
        }
        if (this.spatialModelSource === "generated" && String(this.query.visual_asset_id || "") === String(visualAssetId)) {
          this.renderSpatialViewer();
        }
      } catch (error) {
        if (String(this.query.visual_asset_id || "") === String(visualAssetId)) {
          this.photoCadGeneration = {
            status: "error",
            visual_asset_id: visualAssetId,
            candidate_id: "",
            message: "照片 CAD 生成失败。",
            error: error.message || String(error),
          };
        }
      } finally {
        this.paintIcons();
      }
    },
    async runQuery() {
      this.loading = true;
      this.startAgentProgress();
      this.queryError = "";
      try {
        this.result = await this.api("/api/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.query),
        });
        this.spatialGuidance = this.result.spatial_guidance || this.spatialGuidance;
        if (this.spatialGuidance?.model_id) this.selectedSpatialModelId = this.spatialGuidance.model_id;
        this.updateCurrentSession(this.result);
        this.prepareFeedbackDraft();
        this.renderSpatialViewer();
      } catch (error) {
        this.queryError = `检修方案生成失败：${error.message || error}`;
      } finally {
        this.loading = false;
        this.stopAgentProgress(Boolean(this.result));
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
      const response = await this.api(`/api/cases/${id}/approve`, { method: "POST" });
      this.latestKnowledgeWrite = response.knowledge_write || null;
      await this.refreshAll();
    },
    async generateCandidateCadFromCurrentImage() {
      if (!this.query.visual_asset_id) {
        this.candidateCadStatus = "请先上传现场照片，再生成候选 CAD。";
        return;
      }
      this.candidateCadStatus = "正在生成 CAD spec、CadQuery/OpenSCAD 代码和渲染预览...";
      try {
        const response = await this.api("/api/cad/candidates/from-visual", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            visual_asset_id: this.query.visual_asset_id,
            equipment: this.query.equipment,
            model: this.query.model,
            generator: "cadquery_openscad",
          }),
        });
        this.candidateCadStatus = `已生成候选 CAD #${response.candidate.id}，等待机械审核。`;
        this.selectedCandidateCadId = response.candidate.id;
        await this.refreshAll();
      } catch (error) {
        this.candidateCadStatus = `候选 CAD 生成失败：${error.message || error}`;
      } finally {
        this.paintIcons();
      }
    },
    async approveCandidateCad(id) {
      await this.api(`/api/cad/candidates/${id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: "approved_candidate",
          reviewer: "ME-R2",
          notes: "人工审核通过：仅作为候选结构链资产，不用于尺寸测量、制造或安全放行。",
        }),
      });
      this.candidateCadStatus = `候选 CAD #${id} 已批准入候选资产池。`;
      await this.refreshAll();
    },
    selectCandidateCad(item) {
      if (!item) return;
      this.selectedCandidateCadId = item.id;
      this.candidateCadSpecDraft = JSON.stringify(item.editable_spec || item.cad_spec || {}, null, 2);
      this.candidateCadReviewStatus = `当前审核候选 CAD #${item.id}：${this.candidateCadStatusLabel(item.status)}。`;
      this.paintIcons();
    },
    async patchCandidateCadSpec() {
      const selected = this.selectedCandidateCadAsset;
      if (!selected) return;
      let spec;
      try {
        spec = JSON.parse(this.candidateCadSpecDraft || "{}");
      } catch (error) {
        this.candidateCadReviewStatus = `CAD spec 不是合法 JSON：${error.message || error}`;
        return;
      }
      const response = await this.api(`/api/cad/candidates/${selected.id}/spec`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parameters: spec.parameters || {},
          component_keys: spec.component_keys || selected.cad_spec?.component_keys || [],
          review_notes: "前端审核工位人工修正 CAD spec。",
        }),
      });
      this.candidateCadReviewStatus = `候选 CAD #${response.candidate.id} 的 spec 已保存，需重新渲染后复核。`;
      await this.refreshAll();
    },
    async rerenderCandidateCad(id) {
      if (!id) return;
      const response = await this.api(`/api/cad/candidates/${id}/render`, { method: "POST" });
      this.candidateCadReviewStatus = `候选 CAD #${response.candidate.id} 已重新生成 STEP/STL/GLB/PNG 产物。`;
      await this.refreshAll();
    },
    async promoteCandidateCad(id) {
      const selected = this.candidateCadAssets.find((item) => String(item.id) === String(id));
      if (!selected) return;
      const response = await this.api(`/api/cad/candidates/${id}/promote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_title: `候选 CAD：${this.partTreeEquipmentLabel(selected.equipment)} ${selected.model || ""}`.trim(),
          component_binding_mode: "candidate_component_key",
        }),
      });
      this.candidateCadReviewStatus = `候选 CAD #${id} 已晋升为结构链资产：${response.promotion.model_id}。`;
      await this.refreshAll();
    },
    async rejectCandidateCad(id) {
      await this.api(`/api/cad/candidates/${id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: "rejected",
          reviewer: "ME-R2",
          notes: "人工审核驳回：结构、孔位或部件相对位置不足以进入候选资产池。",
        }),
      });
      this.candidateCadStatus = `候选 CAD #${id} 已驳回。`;
      await this.refreshAll();
    },
    selectResourcePage(pageId) {
      this.activeResourcePage = pageId;
      const meta = this.activeResourcePageMeta;
      this.resourceOperationStatus = `${meta.label}页面已打开。${meta.summary}`;
      this.paintIcons();
    },
    async runActiveResourcePage() {
      const page = this.activeResourcePage;
      if (page === "comparison") return this.runComparison(20);
      if (page === "ingest") return this.ingestManuals();
      if (page === "index") return this.rebuildIndex();
      if (page === "samples") return this.generateSampleData();
      if (page === "quick_eval") return this.runEval(20);
      if (page === "full_eval") return this.runEval(0);
      if (page === "models") return this.discoverModels();
      return null;
    },
    startResourceOperation(type) {
      const meta = this.resourcePages.find((item) => item.id === type) || this.activeResourcePageMeta || {};
      this.resourceOperationResult = {
        type,
        label: meta.label || type,
        status: "running",
        startedAt: new Date().toLocaleTimeString(),
        payload: null,
      };
      this.paintIcons();
    },
    finishResourceOperation(type, payload) {
      const meta = this.resourcePages.find((item) => item.id === type) || this.activeResourcePageMeta || {};
      this.resourceOperationResult = {
        type,
        label: meta.label || type,
        status: "done",
        payload,
        completedAt: new Date().toLocaleTimeString(),
      };
      this.adminResult = JSON.stringify(payload, null, 2);
      this.paintIcons();
    },
    async ingestManuals() {
      this.activeResourcePage = "ingest";
      this.startResourceOperation("ingest");
      this.resourceOperationStatus = "正在入库手册...";
      const result = await this.api("/api/admin/ingest-manuals", { method: "POST" });
      this.finishResourceOperation("ingest", result);
      this.resourceOperationStatus = "手册入库完成，资源与索引状态已刷新。";
      await this.refreshAll();
    },
    async rebuildIndex() {
      this.activeResourcePage = "index";
      this.startResourceOperation("index");
      this.resourceOperationStatus = "正在重建检索索引...";
      const result = await this.api("/api/admin/rebuild-index", { method: "POST" });
      this.finishResourceOperation("index", result);
      this.resourceOperationStatus = "索引重建完成，后续检索会使用最新索引。";
      await this.refreshAll();
    },
    async generateSampleData() {
      this.activeResourcePage = "samples";
      this.startResourceOperation("samples");
      this.resourceOperationStatus = "正在生成演示样例...";
      const result = await this.api("/api/admin/generate-sample-data", { method: "POST" });
      this.finishResourceOperation("samples", result);
      this.resourceOperationStatus = "样例生成完成，黄金链路数据已刷新。";
      await this.refreshAll();
    },
    async runEval(maxQuestions = 20) {
      const operationType = maxQuestions ? "quick_eval" : "full_eval";
      this.activeResourcePage = operationType;
      this.startResourceOperation(operationType);
      this.resourceOperationStatus = maxQuestions ? "正在运行快速评测..." : "正在运行完整评测...";
      const suffix = maxQuestions ? `?max_questions=${maxQuestions}` : "";
      const result = await this.api(`/api/eval/run${suffix}`, { method: "POST" });
      this.finishResourceOperation(operationType, result);
      this.resourceOperationStatus = maxQuestions ? "快速评测完成，指标已刷新。" : "完整评测完成，指标已刷新。";
      await this.refreshAll();
    },
    async runComparison(maxQuestions = 20) {
      this.activeResourcePage = "comparison";
      this.startResourceOperation("comparison");
      this.resourceOperationStatus = "正在运行四组对比评测...";
      const suffix = maxQuestions ? `?max_questions=${maxQuestions}` : "";
      const result = await this.api(`/api/eval/run-comparison${suffix}`, { method: "POST" });
      this.finishResourceOperation("comparison", result);
      this.resourceOperationStatus = "四组对比评测完成，评测证明数据已刷新。";
      await this.refreshAll();
    },
    async discoverModels() {
      this.activeResourcePage = "models";
      this.startResourceOperation("models");
      this.resourceOperationStatus = "正在探测模型路由...";
      const result = await this.api("/api/models");
      this.modelResults = result.results;
      this.finishResourceOperation("models", result);
      this.resourceOperationStatus = "模型探测完成，可在模型页面查看可用模型与缺失原因。";
      this.paintIcons();
    },
    async loadSpatialModels() {
      const response = await this.api(`/api/3d/models?equipment=${encodeURIComponent(this.query.equipment)}`);
      this.spatialModels = response.models || [];
      if (!this.spatialModels.length) {
        this.selectedSpatialModelId = "";
        this.selectedSpatialModel = { components: [] };
        this.renderSpatialViewer();
        return;
      }
      if (this.spatialModels.length && !this.spatialModels.some((item) => item.id === this.selectedSpatialModelId)) {
        this.selectedSpatialModelId = this.spatialModels[0].id;
      }
      if (this.selectedSpatialModelId) await this.loadSpatialModelDetail();
    },
    async loadSpatialModelDetail() {
      if (!this.selectedSpatialModelId && this.spatialModels.length) this.selectedSpatialModelId = this.spatialModels[0].id;
      if (!this.selectedSpatialModelId) return;
      this.selectedSpatialModel = await this.api(`/api/3d/models/${this.selectedSpatialModelId}`);
      this.spatialSection = false;
      this.ensureSpatialCalibrationComponentKey();
      this.renderSpatialViewer();
    },
    ensureSpatialCalibrationComponentKey() {
      const components = this.spatialCalibrationComponents || [];
      const isValid = components.some((item) => item.component_key === this.spatialCalibrationComponentKey);
      if (!isValid) {
        this.spatialCalibrationComponentKey = components[0]?.component_key || "";
      }
      return this.spatialCalibrationComponentKey;
    },
    renderSpatialViewer() {
      nextTick(() => {
        const container = this.$refs.spatialCanvas;
        if (!container || !window.A1ThreeWorkbench) return;
        const viewerCanvas = this.spatialViewer?.renderer?.domElement;
        const staleViewer = this.spatialViewer && (
          this.spatialViewer.container !== container
          || !viewerCanvas
          || !viewerCanvas.isConnected
          || !container.contains(viewerCanvas)
        );
        if (staleViewer) {
          this.spatialViewer.dispose?.();
          this.spatialViewer = null;
        }
        if (!this.spatialViewer) this.spatialViewer = new window.A1ThreeWorkbench(container);
        const guidance = this.activeSpatialGuidance;
        const guidanceMatchesCurrentEquipment = !guidance.equipment || guidance.equipment === this.query.equipment;
        const hasGeneratedGuidance = Boolean(guidance.model_id) && guidanceMatchesCurrentEquipment;
        let model, highlights;
        if (this.spatialModelSource === "generated" && this.generatedCadModel) {
          const gen = this.generatedCadModel;
          model = gen;
          highlights = gen.highlighted_components || [];
        } else if (hasGeneratedGuidance && guidance.components?.length) {
          model = {
              id: guidance.model_id,
              equipment: guidance.equipment,
              title: guidance.model_title,
              source_type: guidance.source_type,
              viewer_mode: guidance.viewer_mode,
              mesh_path: guidance.mesh_path,
              processed_mesh_path: guidance.processed_mesh_path,
              processed_mesh_url: guidance.processed_mesh_url,
              source_cad_path: guidance.source_cad_path,
              sidecar_path: guidance.sidecar_path,
              conversion_report: guidance.conversion_report,
              embed_url: guidance.embed_url,
              source_url: guidance.source_url,
              attribution: guidance.attribution,
              asset_status: guidance.asset_status,
              license: guidance.license,
              cad_bridge: guidance.cad_bridge,
              node_bindings: guidance.node_bindings,
              inspection_views: guidance.inspection_views,
              preview_path: guidance.preview_path,
              components: guidance.components,
            };
          highlights = guidance.highlighted_components || [];
        } else {
          model = this.selectedSpatialModel;
          highlights = guidance.highlighted_components || [];
        }
        const modelComponentKeys = new Set((model?.components || []).map((item) => item.component_key || item.key).filter(Boolean));
        const calibrationKey = this.ensureSpatialCalibrationComponentKey();
        this.spatialViewer.setModel(model, highlights);
        this.spatialViewer.setSection(this.spatialSection);
        this.spatialViewer.setCalibrationMode?.({
          enabled: this.spatialCalibrationMode,
          componentKey: calibrationKey,
          onChange: (payload) => {
            this.adminResult = JSON.stringify({
              calibration_saved: true,
              ...payload,
              note: "已保存到浏览器本地存储；需要正式固化时可复制锚点写入辅助标注。",
            }, null, 2);
            this.renderSpatialViewer();
          },
        });
        this.spatialViewer.resize?.();
        const activeKey = modelComponentKeys.has(this.focusedSpatialComponentKey)
          ? this.focusedSpatialComponentKey
          : modelComponentKeys.has(guidance.scene_state?.active_component_key)
            ? guidance.scene_state.active_component_key
            : "";
        if (activeKey) this.spatialViewer.focusComponent(activeKey);
      });
    },
    resetSpatialView() {
      if (this.spatialViewer?.resetView) this.spatialViewer.resetView();
    },
    toggleSpatialSection() {
      this.spatialSection = !this.spatialSection;
      if (this.spatialViewer?.setSection) this.spatialViewer.setSection(this.spatialSection);
    },
    focusSpatialComponent(componentKey) {
      this.focusedSpatialComponentKey = componentKey || "";
      if (this.spatialViewer?.focusComponent) this.spatialViewer.focusComponent(this.focusedSpatialComponentKey);
    },
    applySpatialCalibrationMode() {
      const calibrationKey = this.ensureSpatialCalibrationComponentKey();
      this.spatialViewer?.setCalibrationMode?.({
        enabled: this.spatialCalibrationMode,
        componentKey: calibrationKey,
        onChange: (payload) => {
          this.adminResult = JSON.stringify({
            calibration_saved: true,
            ...payload,
            note: "已保存到浏览器本地存储；需要正式固化时可复制锚点写入辅助标注。",
          }, null, 2);
          this.renderSpatialViewer();
        },
      });
    },
    toggleSpatialCalibration() {
      this.spatialCalibrationMode = !this.spatialCalibrationMode;
      this.applySpatialCalibrationMode();
    },
    switchSpatialModelSource(source) {
      this.spatialModelSource = source;
      this.spatialSection = false;
      this.ensureSpatialCalibrationComponentKey();
      if (!this.spatialCalibrationComponents.some((item) => item.component_key === this.focusedSpatialComponentKey)) {
        this.focusedSpatialComponentKey = "";
      }
      this.renderSpatialViewer();
      this.paintIcons();
    },
    async generateCadFromCurrentPhoto() {
      if (!this.query.visual_asset_id) {
        this.spatialModelSource = "generated";
        this.queryError = "请先在左侧上传一张现场照片，系统会自动生成照片 CAD。";
        this.renderSpatialViewer();
        this.paintIcons();
        return;
      }
      this.queryError = "";
      this.spatialModelSource = "generated";
      await this.autoGenerateCadFromUploadedImage({ visual_asset_id: this.query.visual_asset_id });
      this.ensureSpatialCalibrationComponentKey();
      this.renderSpatialViewer();
      this.paintIcons();
    },
    async runSpatialGuidance() {
      this.queryError = "";
      try {
        const payload = {
          text: this.query.text,
          equipment: this.query.equipment,
          model: this.query.model,
          visual_asset_id: this.query.visual_asset_id,
          sop_steps: this.result?.sop_steps || [],
          compliance: this.result?.compliance || [],
        };
        this.spatialGuidance = await this.api("/api/3d/guidance", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        this.selectedSpatialModelId = this.spatialGuidance.model_id;
        this.focusedSpatialComponentKey = this.spatialGuidance.scene_state?.active_component_key || "";
        this.updateCurrentSession(this.result);
        this.renderSpatialViewer();
      } catch (error) {
        this.queryError = `3D 导引生成失败：${error.message || error}`;
      }
    },
    async startOnePhotoReconstruction() {
      if (!this.query.visual_asset_id) return;
      const result = await this.api("/api/3d/reconstruct/one-photo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ visual_asset_id: this.query.visual_asset_id, provider: "cached_demo" }),
      });
      this.reconstructionJobs.unshift(result.job);
      this.adminResult = JSON.stringify(result, null, 2);
    },
    selectMultiPhotoFiles(event) {
      this.multiPhotoFiles = Array.from(event.target.files || []);
    },
    async startMultiPhotoReconstruction() {
      if (!this.multiPhotoFiles.length) return;
      const form = new FormData();
      this.multiPhotoFiles.forEach((file) => form.append("files", file));
      const result = await this.api(`/api/3d/reconstruct/multi-photo?equipment=${encodeURIComponent(this.query.equipment)}`, {
        method: "POST",
        body: form,
      });
      this.reconstructionJobs.unshift(result.job);
      this.adminResult = JSON.stringify(result, null, 2);
    },
    spatialComponentLabel(componentKey) {
      const components = this.activeSpatialGuidance.components || this.selectedSpatialModel.components || [];
      const matched = components.find((item) => item.component_key === componentKey);
      return matched?.label || this.componentDisplayName(componentKey);
    },
    compactStepLabel(steps) {
      const values = [...new Set((steps || []).map((item) => Number(item)).filter(Boolean))].sort((a, b) => a - b);
      if (!values.length) return "未绑定";
      const ranges = [];
      let start = values[0];
      let previous = values[0];
      for (let index = 1; index <= values.length; index += 1) {
        const current = values[index];
        if (current === previous + 1) {
          previous = current;
          continue;
        }
        ranges.push(start === previous ? `#${start}` : `#${start}-#${previous}`);
        start = current;
        previous = current;
      }
      return ranges.join(" / ");
    },
    compactListLabel(items, limit = 2) {
      const values = [...new Set((items || []).filter(Boolean).map((item) => this.localizedEngineeringText(item)))];
      if (!values.length) return "按证据执行";
      const visible = values.slice(0, limit).join(" / ");
      return values.length > limit ? `${visible} 等${values.length}类` : visible;
    },
    localizedEngineeringText(value) {
      const raw = String(value || "");
      if (!raw) return "";
      const exact = {
        "网页 GLB": "网页三维模型",
        "sidecar 标注": "辅助标注",
        "SOP 部件绑定": "作业步骤部件绑定",
        "CAD 原件": "结构原件",
        "named_glb_node_with_semantic_hotspots": "命名三维节点与语义热点",
        "semantic_hotspot_overlay": "语义热点标注",
        "local_glb": "本地结构模型",
      }[raw];
      if (exact) return exact;
      return raw
        .replace(/CAD\/GLB/g, "结构模型")
        .replace(/CAD\/mesh/g, "结构模型")
        .replace(/component_key/g, "部件标识")
        .replace(/\bSOP\b/g, "作业步骤")
        .replace(/\b3D\b/g, "三维")
        .replace(/sidecar/g, "辅助标注")
        .replace(/mesh/g, "网格模型")
        .replace(/CAD 来源/g, "结构来源");
    },
    bridgeTraceLabel(label) {
      return this.localizedEngineeringText(label);
    },
    bridgeTraceExplanation(text) {
      return this.localizedEngineeringText(text);
    },
    cadNodeDisplayName(value) {
      const raw = String(value || "");
      if (!raw) return "语义热点";
      const component = this.componentDisplayName(raw);
      if (component && component !== raw) return component;
      if (/cad[_-]?mesh/i.test(raw)) return "结构模型节点";
      return this.localizedEngineeringText(raw.replace(/[_-]+/g, " "));
    },
    activeSafetyChecks() {
      return this.activeSpatialGuidance.safety_gate?.required_checks || [];
    },
    activeSafetyDecision() {
      return this.activeSpatialGuidance.safety_gate?.decision || "生成导引后显示安全放行结论。";
    },
    activeSpatialMaturity() {
      return this.activeSpatialGuidance.model_maturity || {
        label: this.selectedSpatialModel.viewer_mode === "local_glb" ? "授权本地模型" : "待加载模型",
        level: this.selectedSpatialModel.viewer_mode || "unknown",
        binding_mode: this.selectedSpatialModel.node_bindings?.binding_mode || "unknown",
        object_level_binding: Boolean(this.selectedSpatialModel.node_bindings?.exact_cad_face_binding),
        limitations: [],
      };
    },
    spatialProfessionalGaps() {
      return this.activeSpatialGuidance.professional_gaps || this.activeSpatialMaturity().limitations || [];
    },
    cadBridge() {
      return this.activeSpatialGuidance.cad_bridge || this.selectedSpatialModel.cad_bridge || {
        title: "结构模型双证据链",
        cad_source: {},
        glb_viewer: {},
        sidecar: {},
        conversion: {},
        trace_chain: [],
        component_bindings: [],
        limitations: [],
      };
    },
    bridgeComponentBindings() {
      const focused = this.focusedSpatialComponentKey;
      const bindings = this.cadBridge().component_bindings || [];
      const sorted = [...bindings].sort((a, b) => {
        if (focused && a.component_key === focused) return -1;
        if (focused && b.component_key === focused) return 1;
        return (b.sop_step_count || 0) - (a.sop_step_count || 0);
      });
      return sorted.slice(0, 6);
    },
    bridgeFileName(path) {
      const value = String(path || "");
      return value.split(/[\\/]/).pop() || "未提供";
    },
    bridgeHash(value) {
      return value ? `${String(value).slice(0, 12)}...` : "未提供";
    },
    bridgeStatusLabel(status) {
      return {
        verified: "已验证",
        ready: "可用",
        missing: "缺失",
        waiting_for_guidance: "等待导引",
      }[status] || status || "未知";
    },
    openCandidateCadViewer(item, view = "iso") {
      if (!item) return;
      this.selectCandidateCad(item);
      this.candidateCadLightbox = {
        open: true,
        assetId: item.id,
        view,
        rotation: 0,
        mode: "glb",
      };
      nextTick(() => {
        this.paintIcons();
        this.renderCandidateCadGlbViewer();
      });
    },
    closeCandidateCadViewer() {
      this.disposeCandidateCadGlbViewer();
      this.candidateCadLightbox.open = false;
    },
    setCandidateCadViewerMode(mode) {
      if (!["glb", "render"].includes(mode)) return;
      this.candidateCadLightbox.mode = mode;
      if (mode === "glb") {
        nextTick(() => this.renderCandidateCadGlbViewer());
      } else {
        this.disposeCandidateCadGlbViewer();
      }
      nextTick(() => this.paintIcons());
    },
    setCandidateCadViewerView(view) {
      if (!this.candidateCadViewerViews.includes(view)) return;
      this.candidateCadLightbox.mode = "render";
      this.disposeCandidateCadGlbViewer();
      this.candidateCadLightbox.view = view;
      nextTick(() => this.paintIcons());
    },
    rotateCandidateCadViewer(delta) {
      const current = Number(this.candidateCadLightbox.rotation || 0);
      this.candidateCadLightbox.rotation = current + delta;
      nextTick(() => this.paintIcons());
    },
    resetCandidateCadViewerRotation() {
      this.candidateCadLightbox.rotation = 0;
      nextTick(() => this.paintIcons());
    },
    disposeCandidateCadGlbViewer() {
      const viewer = this.candidateCadGlbViewer;
      if (!viewer) return;
      viewer.disposed = true;
      if (viewer.raf) cancelAnimationFrame(viewer.raf);
      if (viewer.resizeObserver) viewer.resizeObserver.disconnect();
      (viewer.cleanup || []).forEach((fn) => fn());
      if (viewer.scene) {
        viewer.scene.traverse((object) => {
          if (object.geometry?.dispose) object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.filter(Boolean).forEach((material) => material.dispose?.());
        });
      }
      if (viewer.renderer) {
        viewer.renderer.dispose?.();
        viewer.renderer.forceContextLoss?.();
        viewer.renderer.domElement?.remove();
      }
      if (viewer.container) viewer.container.innerHTML = "";
      this.candidateCadGlbViewer = null;
      this.candidateCadGlbViewerToken = "";
    },
    renderCandidateCadGlbViewer() {
      nextTick(() => {
        const container = this.$refs.candidateCadGlbCanvas;
        const item = this.candidateCadViewerAsset;
        if (!container || !item || !this.candidateCadLightbox.open || this.candidateCadLightbox.mode !== "glb") return;
        if (this.candidateCadGlbViewer?.assetId === item.id && this.candidateCadGlbViewer.container === container) {
          this.candidateCadGlbViewer.resize?.();
          return;
        }
        this.disposeCandidateCadGlbViewer();
        const THREE = window.THREE;
        const Loader = THREE?.GLTFLoader;
        if (!THREE || !Loader) {
          container.innerHTML = "<div class='cad-viewer-glb-message'>Three.js 或 GLTFLoader 未加载，无法交互预览 GLB。</div>";
          return;
        }

        container.innerHTML = "<div class='cad-viewer-glb-message'>正在加载 candidate.glb...</div>";
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf5f8fa);
        const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
        const renderer = new THREE.WebGLRenderer({
          antialias: true,
          alpha: false,
          preserveDrawingBuffer: true,
          powerPreference: "high-performance",
        });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.outputEncoding = THREE.sRGBEncoding || renderer.outputEncoding;
        renderer.domElement.tabIndex = 0;
        renderer.domElement.setAttribute("aria-label", "可拖拽旋转的 GLB 候选 CAD 模型");

        container.innerHTML = "";
        container.appendChild(renderer.domElement);

        const group = new THREE.Group();
        scene.add(group);
        scene.add(new THREE.AmbientLight(0xffffff, 0.72));
        const keyLight = new THREE.DirectionalLight(0xffffff, 0.95);
        keyLight.position.set(4, 6, 5);
        scene.add(keyLight);
        const rimLight = new THREE.DirectionalLight(0x9bd7e8, 0.38);
        rimLight.position.set(-3, 2, -4);
        scene.add(rimLight);
        const grid = new THREE.GridHelper(4.8, 16, 0xaebfca, 0xdbe4ea);
        grid.position.y = -1.24;
        scene.add(grid);

        let distance = 4.6;
        const cameraDir = new THREE.Vector3(1.75, 1.08, 2.35).normalize();
        const applyCamera = () => {
          camera.position.copy(cameraDir.clone().multiplyScalar(distance));
          camera.lookAt(0, 0, 0);
        };
        applyCamera();

        const viewer = {
          token: `${item.id}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
          assetId: item.id,
          container,
          scene,
          camera,
          renderer,
          group,
          diagnostics: {
            assetId: item.id,
            status: "loading",
            meshCount: 0,
            box: null,
            scale: null,
            rootPosition: null,
            error: "",
            renderMode: "on_demand",
            renderCount: 0,
            resizeCount: 0,
            lastSize: null,
          },
          cleanup: [],
          raf: 0,
          resizeObserver: null,
          disposed: false,
          renderQueued: false,
          lastSize: { width: 0, height: 0, pixelRatio: 0 },
          render: () => {
            if (viewer.disposed) return;
            renderer.render(scene, camera);
            viewer.diagnostics.renderCount += 1;
          },
          requestRender: () => {
            if (viewer.disposed || viewer.renderQueued) return;
            viewer.renderQueued = true;
            viewer.raf = requestAnimationFrame(() => {
              viewer.renderQueued = false;
              viewer.raf = 0;
              viewer.render();
            });
          },
          resize: () => {
            const rect = container.getBoundingClientRect();
            const width = Math.max(360, Math.floor(rect.width || 720));
            const height = Math.max(340, Math.floor(rect.height || 520));
            const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
            if (
              viewer.lastSize.width === width &&
              viewer.lastSize.height === height &&
              viewer.lastSize.pixelRatio === pixelRatio
            ) {
              return;
            }
            viewer.lastSize = { width, height, pixelRatio };
            renderer.setPixelRatio(pixelRatio);
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
            renderer.setSize(width, height, false);
            viewer.diagnostics.resizeCount += 1;
            viewer.diagnostics.lastSize = viewer.lastSize;
            viewer.requestRender();
          },
        };
        this.candidateCadGlbViewerToken = viewer.token;
        this.candidateCadGlbViewer = Vue.markRaw ? Vue.markRaw(viewer) : viewer;
        window.__candidateCadGlbDiagnostics = viewer.diagnostics;

        let dragging = false;
        let lastPointer = { x: 0, y: 0 };
        const onPointerDown = (event) => {
          dragging = true;
          lastPointer = { x: event.clientX, y: event.clientY };
          renderer.domElement.setPointerCapture?.(event.pointerId);
        };
        const onPointerMove = (event) => {
          if (!dragging) return;
          const dx = event.clientX - lastPointer.x;
          const dy = event.clientY - lastPointer.y;
          group.rotation.y += dx * 0.009;
          group.rotation.x = Math.max(-1.15, Math.min(1.15, group.rotation.x + dy * 0.006));
          lastPointer = { x: event.clientX, y: event.clientY };
          viewer.requestRender();
        };
        const onPointerUp = () => {
          dragging = false;
        };
        const onWheel = (event) => {
          event.preventDefault();
          distance = Math.max(2.1, Math.min(8.4, distance + Math.sign(event.deltaY) * 0.32));
          applyCamera();
          viewer.requestRender();
        };
        renderer.domElement.addEventListener("pointerdown", onPointerDown);
        renderer.domElement.addEventListener("pointermove", onPointerMove);
        renderer.domElement.addEventListener("pointerup", onPointerUp);
        renderer.domElement.addEventListener("pointerleave", onPointerUp);
        renderer.domElement.addEventListener("wheel", onWheel, { passive: false });
        viewer.cleanup.push(
          () => renderer.domElement.removeEventListener("pointerdown", onPointerDown),
          () => renderer.domElement.removeEventListener("pointermove", onPointerMove),
          () => renderer.domElement.removeEventListener("pointerup", onPointerUp),
          () => renderer.domElement.removeEventListener("pointerleave", onPointerUp),
          () => renderer.domElement.removeEventListener("wheel", onWheel),
        );

        viewer.resizeObserver = new ResizeObserver(() => viewer.resize());
        viewer.resizeObserver.observe(container);
        viewer.resize();

        new Loader().load(
          this.candidateCadViewerGlbUrl,
          (gltf) => {
            if (this.candidateCadGlbViewerToken !== viewer.token) return;
            const root = gltf.scene || gltf.scenes?.[0];
            if (!root) {
              viewer.diagnostics.status = "empty_scene";
              container.insertAdjacentHTML("beforeend", "<div class='cad-viewer-glb-message'>GLB 文件未包含可显示场景。</div>");
              return;
            }
            const palette = [0x567080, 0x2f6f9f, 0x168a7a, 0x8a9aa8, 0xd99022, 0x6a7f94];
            let meshIndex = 0;
            root.traverse((object) => {
              if (!object.isMesh) return;
              object.castShadow = true;
              object.receiveShadow = true;
              object.geometry?.computeVertexNormals?.();
              object.material = new THREE.MeshStandardMaterial({
                color: palette[meshIndex % palette.length],
                emissive: palette[meshIndex % palette.length],
                emissiveIntensity: 0.04,
                metalness: 0.18,
                roughness: 0.48,
                side: THREE.DoubleSide,
                polygonOffset: true,
                polygonOffsetFactor: meshIndex * 0.05,
                polygonOffsetUnits: meshIndex * 0.05,
              });
              meshIndex += 1;
            });
            viewer.diagnostics.meshCount = meshIndex;
            group.add(root);
            const box = new THREE.Box3().setFromObject(root);
            const size = box.getSize(new THREE.Vector3());
            const center = box.getCenter(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z, 0.001);
            const scale = 2.8 / maxDim;
            root.scale.setScalar(scale);
            root.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
            viewer.diagnostics.status = "loaded";
            viewer.diagnostics.box = {
              min: box.min.toArray(),
              max: box.max.toArray(),
              size: size.toArray(),
              center: center.toArray(),
            };
            viewer.diagnostics.scale = scale;
            viewer.diagnostics.rootPosition = root.position.toArray();
            distance = Math.max(3.0, Math.min(6.8, 4.1 + maxDim * scale * 0.16));
            applyCamera();
            viewer.resize();
            viewer.requestRender();
          },
          undefined,
          (error) => {
            if (this.candidateCadGlbViewerToken !== viewer.token) return;
            viewer.diagnostics.status = "error";
            viewer.diagnostics.error = String(error?.message || error);
            container.innerHTML = `<div class='cad-viewer-glb-message'>GLB 加载失败：${this.escapeHtml(error?.message || error)}<br><a href='${this.candidateCadViewerGlbUrl}' target='_blank' rel='noopener'>下载 GLB 文件检查</a></div>`;
          },
        );
      });
    },
    handleGlobalKeydown(event) {
      if (event.key === "Escape" && this.candidateCadLightbox.open) {
        this.closeCandidateCadViewer();
      }
    },
    candidateCadFileUrl(item, role) {
      return item?.id ? `/api/cad/candidates/${item.id}/files/${role}` : "#";
    },
    candidateCadRenderUrl(item, view) {
      return this.candidateCadFileUrl(item, `render-${view}`);
    },
    candidateCadStatusLabel(status) {
      return {
        generated: "已生成",
        rendered: "已渲染",
        vlm_scored: "已比对",
        needs_review: "待人工审核",
        approved_candidate: "候选可用",
        rejected: "已驳回",
        promoted_standard_asset: "已晋升标准资产",
      }[status] || status || "未知";
    },
    candidateCadCompareLabel(item) {
      const compare = item?.vlm_compare || {};
      const score = Math.round((compare.similarity_score || 0) * 100);
      return `${this.statusDisplayLabel(compare.status || "needs_review")} · ${score}%`;
    },
    statusDisplayLabel(status) {
      const raw = String(status || "").trim();
      const normalized = raw.toLowerCase();
      return {
        ready: "就绪",
        blocked: "已阻断",
        waiting: "等待中",
        waiting_safety_check: "等待安全确认",
        in_progress: "执行中",
        connected: "已连接",
        degraded: "降级可用",
        empty: "暂无数据",
        done: "已完成",
        pending: "等待中",
        warning: "需关注",
        needs_review: "待人工复核",
        need_review: "待人工复核",
        approved: "已审核",
        unreviewed: "未审核",
        verified: "已验证",
        missing: "缺失",
        local: "本地兜底",
        procedural_fallback: "程序化兜底",
        fallback: "兜底",
        semantic_hotspot: "语义热点",
        semantic_hotspot_overlay: "语义热点标注",
        named_glb_node_with_semantic_hotspots: "命名三维节点与语义热点",
        "cadquery.importers.importstep": "结构原件导入工具",
        web_glb: "网页结构模型",
        local_glb: "本地结构模型",
        glb: "三维模型",
        stl: "三维网格",
        step: "结构原件",
        unknown: "未知",
        authorized_local_glb_from_freecad_step: "本地授权结构模型",
        generated: "已生成",
        high: "高",
        medium: "中",
        low: "低",
      }[normalized] || raw || "未知";
    },
    gateStateDisplayLabel(state) {
      return this.statusDisplayLabel(String(state || "").replace(/^NEED_REVIEW$/i, "needs_review"));
    },
    riskDisplayLabel(level) {
      return this.riskLabel(level) || this.statusDisplayLabel(level);
    },
    claimDisplayId(id) {
      const raw = String(id || "").trim();
      if (!raw) return "暂无编号";
      const cleaned = raw.replace(/^claim[_-]?/i, "");
      const parts = cleaned.split(/[_-]+/).filter(Boolean);
      const equipment = { pump: "泵类", motor: "电机", bearing: "轴承", engine: "发动机" }[parts[0]];
      const tail = (equipment ? parts.slice(1) : parts).join("-") || cleaned;
      return `${equipment ? equipment : ""}判断卡 ${tail}`.trim();
    },
    partTreeEquipmentLabel(equipment) {
      return { bearing: "轴承", motor: "电机", pump: "离心泵", engine: "发动机" }[equipment] || equipment || "未知设备";
    },
    partTreeClassificationLabel(classification) {
      return {
        assembly_tree: "原生装配树",
        multi_solid_cad: "STEP 多实体",
        freecad_feature_tree: "FreeCAD 特征树",
        freecad_parametric_or_multi_object: "FreeCAD 多对象",
      }[classification] || classification || "待识别";
    },
    partTreeClassificationTone(classification) {
      if (classification === "assembly_tree") return "assembly";
      if (classification === "multi_solid_cad") return "solid";
      if (String(classification || "").startsWith("freecad")) return "feature";
      return "unknown";
    },
    formatBytes(value) {
      const bytes = Number(value || 0);
      if (!bytes) return "0 B";
      if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    },
    riskLabel(level) {
      return { high: "高", medium: "中", low: "低" }[level] || level;
    },
  },
}).mount("#app");
