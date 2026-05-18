# 结构化视觉理解与 Neo4j 图谱升级说明

## 目标

本升级补齐 A1 方案中的两个短板：

- 多模态视觉能力从“图片 caption”升级为“结构化视觉诊断”：设备、部件、缺陷标签、OCR 文本、流程图节点/边、风险提示和检索关键词。
- 知识图谱从“即时路径拼接”升级为“图数据库投影”：Neo4j 为主实现，SQLite 为无服务降级实现。

SQLite 仍然是业务主库；Neo4j 是可重建的图谱投影。这样不会因为图数据库未连接导致问诊、检索、SOP、案例审核等核心链路中断。

## 视觉链路

上传图片接口：

```text
POST /api/upload-image
```

新增返回字段：

- `visual_asset_id`：结构化视觉资产 ID。
- `visual_analysis.caption`：一句中文视觉概述。
- `visual_analysis.equipment_candidates`：候选设备类型。
- `visual_analysis.component_candidates`：候选部件。
- `visual_analysis.defect_labels`：缺陷/故障标签。
- `visual_analysis.ocr_text`：图中文字识别结果。
- `visual_analysis.flowchart`：流程图节点、边和摘要。
- `visual_analysis.risk_hints`：安全风险提示。
- `visual_analysis.retrieval_keywords`：参与检索的关键词。

查询接口：

```text
POST /api/query
```

新增可选请求字段：

```json
{
  "visual_asset_id": 1
}
```

当传入 `visual_asset_id` 时，系统会把视觉缺陷标签、OCR 文本、部件候选和检索关键词合并进检索上下文，并在回答中返回 `visual_analysis` 和 `visual_evidence`。

## 图谱链路

新增环境变量：

```env
GRAPH_BACKEND=sqlite
GRAPH_SYNC_ON_STARTUP=false
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=
NEO4J_DATABASE=neo4j
```

推荐比赛演示策略：

- 本地和公网演示默认 `GRAPH_BACKEND=sqlite`，保证零外部服务可运行。
- 有 Neo4j Desktop、Docker 或 AuraDB 连接时切换 `GRAPH_BACKEND=neo4j`。
- Neo4j 连接失败时，后端返回 `sqlite_fallback`，并继续提供图谱路径。

新增接口：

```text
GET  /api/graph/status
POST /api/admin/graph/rebuild
GET  /api/visual-assets
```

`/api/query` 新增返回字段：

- `graph_backend`：`sqlite`、`neo4j` 或 `sqlite_fallback`。
- `graph_status`：连接状态、节点数、边数。
- `graph_paths[].nodes`：路径节点。
- `graph_paths[].edges`：路径关系。

## Neo4j 图谱模型

节点类型：

- `Equipment`
- `Component`
- `Fault`
- `Cause`
- `ProcedureStep`
- `SafetyRule`
- `ManualChunk`
- `Case`
- `VisualAsset`

关系类型：

- `HAS_COMPONENT`
- `HAS_FAULT`
- `HAS_CAUSE`
- `HAS_STEP`
- `HAS_SAFETY_RULE`
- `CITED_BY`
- `OBSERVED_IN`

当前实现使用确定性节点 ID，可从 SQLite 业务数据重建图谱。提交包不包含 Neo4j 数据库文件。

## 验证命令

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api.py::test_upload_image_creates_structured_visual_asset tests\test_api.py::test_query_uses_visual_asset_structured_analysis tests\test_api.py::test_graph_status_rebuild_and_query_paths_use_graph_backend -q
.\.venv\Scripts\python.exe -m pytest -q
node --check frontend\app.js
```

## 答辩表达

可以强调：

- 图片不是只生成自然语言 caption，而是进入结构化视觉资产库。
- OCR、流程图和缺陷标签都能进入检索上下文。
- 图谱不是前端临时画图，而是可以重建、查询、降级的图数据库投影。
- Neo4j 可作为正式图数据库演示；无 Neo4j 时 SQLite fallback 保障系统稳定可运行。
