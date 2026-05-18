# Tri-MRO UI 重构交接文档

生成日期：2026-05-15
目标读者：UI 设计师、前端重构人员、答辩材料设计人员
项目路径：`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant`

## 1. 项目一句话定位

Tri-MRO 是面向中国软件杯 A1 赛题的 **可信设备检修作业控制平台**。

它不是一个普通维修问答机器人，也不是单纯的 CAD 展示工具。它的核心是把一次设备检修任务收束成一条可执行、可追责的闭环：

```text
现场输入
→ OCR/VLM 现场感知
→ 证据检索
→ Claim Card 检修判断卡
→ CAD/部件结构定位
→ SOP 作业票
→ Safety Gate 安全闸门
→ 案例沉淀
→ 人工审核
→ 图谱/索引更新
→ 评测证明
```

对外表达建议：

> 普通系统回答“怎么修”，Tri-MRO 回答“为什么这么判断、具体修哪里、按什么安全条件修、修完如何沉淀为组织知识”。

## 2. A1 赛题要求映射

官方 A1 主题是：**基于多模态大模型技术的设备检修知识检索与作业系统**。

UI 重构时必须覆盖以下赛题能力，不要把它们分散成互不相关的功能块。

| 赛题能力 | 项目对应模块 | UI 上应该怎么体现 |
| --- | --- | --- |
| PC Web 或 App 可视化界面 | 当前为 PC Web 工作台 | 首页直接进入检修任务，不做营销页 |
| 文本、故障图片、设备型号输入 | 检修任务台、图片上传、型号字段 | 左侧或顶部固定为“现场输入” |
| 多模态知识检索 | RAG + 图片 caption + OCR/VLM + 图谱 | 以“证据链”展示，不只显示答案 |
| 跨模态匹配 | 图片线索进入检索、component_key 映射 | 显示“图片识别到什么、映射到哪个部件” |
| 检修手册调取 | citations、manual refs | 引用卡必须有来源、章节、页码/摘要 |
| 标准化作业指引 | SOP 作业票 | 以步骤、工具、风险、验收标准呈现 |
| 合规校验提醒 | Safety Gate | 未确认断电/泄压/PPE 时阻断 |
| 个性化流程推送 | equipment + maintenance_level | 不同设备和检修等级展示不同 SOP |
| 一线案例上传 | 案例沉淀页 | 从当前任务生成案例草稿 |
| 案例审核后入库 | Knowledge Write Pipeline | 审核状态、影响范围、回滚号 |
| 知识图谱更新 | graph_store、Knowledge Write Pipeline | 展示当前任务证据子图，而非全量乱图 |
| 人工修正模型输出 | feedback | 在结果页提供“人工修正与标注”入口 |

## 3. 当前核心创新机制

当前项目最应该围绕四个对象重构 UI，而不是围绕技术名词堆页面。

### 3.1 Claim Card 检修判断卡

后端来源：`backend/app/claim_card.py`
接口字段：`/api/query -> primary_claim_card`

作用：每个故障判断都必须结构化，并同时绑定证据、结构、作业、安全、复核策略。

核心字段：

```json
{
  "claim_id": "claim_pump_xxx",
  "fault_claim": "机械密封泄漏可能与密封端面磨损或安装偏差有关",
  "confidence_level": "high|medium|low|insufficient",
  "evidence_budget": {},
  "evidence_chain": {},
  "structure_chain": {},
  "operation_chain": {},
  "fmea_risk_chain": {},
  "safety_gate": {},
  "review_policy": {}
}
```

UI 建议：Claim Card 应该是检修任务台的主结果，不应被普通“故障判断”卡片淹没。

### 3.2 Component Contract 部件知识契约

后端来源：`backend/app/component_contracts.py`
接口字段：`primary_claim_card.structure_chain.component_contract`、`/api/3d/guidance`

作用：统一 OCR/VLM、RAG、CAD、图谱、SOP、案例中的部件标识。

核心部件：

```text
pump.mechanical_seal
pump.bearing
bearing.outer_ring
bearing.rolling_elements
motor.bearing
motor.shaft
engine.spark_plug
engine.cylinder_head
```

UI 上必须显示：

- 部件中文名和 `component_key`
- 识别别名，例如“机械密封 / 密封端 / shaft seal”
- 常见故障
- 视觉线索
- 手册关键词
- 必要安全闸门
- CAD 绑定等级

绑定等级必须诚实表达：

| 等级 | 含义 | 当前项目状态 |
| --- | --- | --- |
| 设备级 | 只知道设备类型 | 兜底状态 |
| 部件级 | 知道部件，例如机械密封、轴承 | 主线能力 |
| 锚点级 | CAD/GLB 有可点击热点或对象锚点 | 轴承较稳，其他设备多为语义热点 |
| 几何/面级 | CAD 面、尺寸、装配约束级绑定 | 当前不主打 |

### 3.3 Safety Gate 安全闸门状态机

后端来源：`backend/app/safety_gate.py`
接口字段：`primary_claim_card.safety_gate`

作用：把“安全提醒”升级成“作业控制”。未满足安全条件时，系统不允许高风险步骤进入下一步。

状态：

```text
DRAFT
WAITING_SAFETY_CHECK
BLOCKED
READY
IN_PROGRESS
NEED_REVIEW
COMPLETED
ARCHIVED
```

UI 上必须显著展示：

- 当前状态，例如 `BLOCKED`
- 阻断原因，例如“未确认断电挂牌、泄压、PPE”
- 必要确认项
- 审计日志
- 当前是否允许进入下一步

这应该是答辩中最强的“可信系统”演示点。

### 3.4 Knowledge Write Pipeline 知识写入流水线

后端来源：`backend/app/knowledge_write_pipeline.py`
接口字段：`/api/cases/{case_id}/approve -> knowledge_write`

作用：案例不是上传后马上污染知识库，而是经过审核、影响分析、图谱更新、索引更新和回归测试记录。

UI 上必须展示：

```text
案例草稿
→ 待审核
→ 审核通过/驳回
→ 影响部件
→ 图谱更新
→ 索引更新
→ 回滚号
→ 回归评测结果
```

## 4. 当前页面结构

当前前端主文件：

- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`
- `frontend/three-workbench.js`

当前主导航有 6 个一级模块：

```text
检修任务台
CAD 结构工位
案例沉淀
证据链图谱
评测证明
资源与模型
```

当前问题：

- 功能过多，一级页面承担了过多职责。
- “资源与模型”页面同时放了手册入库、评测、模型探测、图片 gate、3D 资产、候选 CAD、零件树候选、模型列表，信息密度过高。
- CAD 页面同时放标准 GLB、SOP 联动、部件校准、photo-to-3D、CAD-3D 证据、成熟度说明，容易让评委误解主线。
- 检修任务台中 Claim Card、普通诊断卡、SOP、合规、模型复核、人工修正、引用、图谱、Agent trace 都在同一屏堆叠。
- 图谱页面已经从全量乱图改成证据链路径，但仍可以进一步围绕当前 Claim Card 简化。

## 5. 推荐重构后的信息架构

建议 UI 不再按技术模块分，而按“检修任务生命周期”分。

### 5.1 一级导航建议

```text
1. 检修任务
2. 结构工位
3. 作业票与安全
4. 知识沉淀
5. 评测与资源
```

也可以保留 6 个页面，但建议视觉层级变成：

| 页面 | 是否主线 | 目标 |
| --- | --- | --- |
| 检修任务 | 主线 P0 | 输入、Claim Card、证据预算、核心判断 |
| 结构工位 | 主线 P0 | CAD/GLB、部件定位、SOP 联动、绑定等级 |
| 作业票与安全 | 主线 P0 | SOP、工具备件、验收标准、Safety Gate |
| 知识沉淀 | 主线 P0 | 从任务生成案例、审核、写入流水线 |
| 证据链图谱 | 主线 P1 | 当前 Claim Card 的证据路径解释 |
| 评测与资源 | 支撑 P1 | 指标、资源验证、模型状态、候选 CAD 实验 |

如果只做 5 个一级模块，可以把“证据链图谱”嵌入“检修任务”的右侧抽屉或详情页。

### 5.2 全局任务条

全局顶部应该始终展示当前任务状态，数据来自 `/api/query -> workflow_state`。

建议字段：

```text
任务 ID
设备类型
型号
当前部件 component_key
证据分
Safety Gate 状态
当前阶段
下一步建议
```

当前已有状态条位于 `frontend/index.html` 的 `workflow-state-strip`，可以保留，但建议重做视觉层级。

## 6. 页面级重构说明

### 6.1 检修任务页

目标：用户完成现场输入，并获得结构化 Claim Card。

主要信息区：

1. 现场输入
   - 设备类型
   - 设备型号
   - 检修等级
   - 故障描述
   - 图片上传
   - 视觉描述/OCR/VLM 标签

2. Claim Card 主结果
   - 故障判断
   - 置信等级
   - Evidence Budget 分数
   - 证据缺口
   - 是否需要人工复核

3. 三链对齐摘要
   - 证据链：手册、案例、图谱、视觉证据数量
   - 结构链：设备、部件、CAD 绑定等级
   - 作业链：SOP 步数、安全闸门状态

4. 关键操作
   - 进入结构工位
   - 查看作业票
   - 从当前任务生成案例
   - 记录人工修正

建议不要在首屏完整展开：

- 所有 citations 全列表
- 多 Agent trace
- 图谱路径明细
- 模型复核全文

这些可以放到“详情抽屉”或二级标签。

### 6.2 结构工位页

目标：展示故障定位到哪个 CAD/GLB 部件，以及这个定位是否可信。

主要布局建议：

```text
左侧：任务/部件候选/设备切换
中间：3D GLB 视窗
右侧：Component Contract + SOP 当前步骤 + 安全状态
底部：SOP 步骤时间线
```

必须强调：

- GLB 是浏览器展示资产。
- STEP/FCStd/CAD 原件是工程来源证据。
- sidecar 是部件语义标注。
- 当前大多是语义热点或锚点，不是 CAD 面级尺寸测量。

应该保留：

- 模型来源
- 许可证
- SHA256
- 转换报告
- 绑定等级
- 人工校准入口

应该弱化：

- photo-to-3D
- 候选 CAD 生成
- 零件树候选

这些放到“实验能力”折叠区或资源页，不要占据主线。

### 6.3 作业票与安全页

当前 SOP 和 Safety Gate 分散在检修任务台与 CAD 工位里，建议拆成独立主页面或右侧固定详情。

页面目标：把大模型建议转成可执行工单。

必须展示：

- 作业票标题
- 设备/型号/检修等级
- 作业步骤
- 每一步风险等级
- 工具备件
- 安全前置条件
- 验收标准
- 当前步骤能否执行
- 审计日志

安全闸门 UI 需要明确三种颜色：

| 状态 | 颜色建议 | 含义 |
| --- | --- | --- |
| READY | 绿色 | 已满足前置条件 |
| WAITING / NEED_REVIEW | 黄色 | 需要人工确认 |
| BLOCKED | 红色 | 系统阻断，不允许继续 |

### 6.4 知识沉淀页

目标：把一次检修任务转成可审核案例，并展示审核后如何进入知识系统。

关键流程：

```text
当前任务
→ 生成案例草稿
→ 待审核
→ 审核通过
→ 写入案例库
→ 更新图谱
→ 更新检索索引
→ 生成回滚号
```

UI 建议：

- 左侧：案例表单
- 中间：待审核列表
- 右侧：Knowledge Write Pipeline 影响分析
- 底部：人工修正记录

必须避免的误解：

- 未审核案例不能显示成“已进入知识库”。
- 驳回案例不能显示为成功写入。
- 当前回滚只是记录 `rollback_id`，真实回滚 API 尚未完整实现，UI 不能夸大。

### 6.5 证据链图谱页

目标：解释当前 Claim Card 的证据路径，不是展示全量知识图谱。

推荐结构：

```text
设备
→ 部件
→ 故障模式
→ 可能原因
→ 检查方法
→ SOP
→ 安全规则
→ 手册/案例/视觉证据
```

当前图谱页已经使用“证据链工作台”的方向，建议继续保留路径卡片形式，减少力导向大图。

### 6.6 评测与资源页

目标：给评委证明系统可信，而不是给开发者堆工具。

建议拆成四个子区域：

1. 创新指标
   - 关键结论可追溯率
   - 三链对齐覆盖率
   - CAD 部件定位 Top-1 / Top-3
   - 高风险步骤阻断率
   - 拒答合理率
   - 知识更新后召回提升率
   - 知识污染拦截率

2. 四组对比
   - 无 RAG
   - 文本 RAG
   - 多模态 RAG
   - Tri-MRO 完整系统

3. 资源验证
   - 手册
   - 图片资产
   - CAD/GLB
   - 许可证
   - SHA256

4. 开发/管理工具
   - 入库手册
   - 重建索引
   - 生成样例
   - 探测模型
   - 候选 CAD

第 4 类建议默认折叠为“高级管理”，不要作为评委主视图。

## 7. 核心 API 速查

后端入口：`backend/app/main.py`

| 方法 | 路径 | UI 用途 |
| --- | --- | --- |
| GET | `/api/health` | 系统状态 |
| GET | `/api/providers` | 模型供应商状态 |
| GET | `/api/devices` | 设备类型和检修等级 |
| POST | `/api/upload-image` | 图片上传、OCR/VLM、视觉资产 |
| POST | `/api/query` | 主检修任务编排，返回 Claim Card、SOP、证据链、CAD guidance |
| GET | `/api/3d/models?equipment=...` | 获取标准 3D/CAD 模型 |
| GET | `/api/3d/models/{model_id}` | 获取模型详情 |
| POST | `/api/3d/guidance` | 根据任务生成 3D 部件导引 |
| POST | `/api/3d/reconstruct/one-photo` | 实验性 one-photo 空间定位 |
| POST | `/api/3d/reconstruct/multi-photo` | 实验性 multi-photo 离线任务包 |
| GET | `/api/cases` | 案例列表 |
| POST | `/api/cases` | 新增待审核案例 |
| POST | `/api/cases/{case_id}/approve` | 审核入库并返回 Knowledge Write Pipeline |
| POST | `/api/feedback` | 人工修正模型输出 |
| GET | `/api/knowledge-graph` | 知识图谱数据 |
| GET | `/api/metrics` | 评测和创新指标 |
| GET | `/api/resources/verification` | 资源验证 |
| POST | `/api/eval/run-comparison` | 四组对比评测 |
| GET | `/api/cad/candidates` | 候选 CAD 资产池 |
| POST | `/api/cad/candidates/from-visual` | 从视觉资产生成候选 CAD |
| POST | `/api/cad/candidates/{id}/review` | 审核候选 CAD |
| POST | `/api/cad/candidates/{id}/promote` | 晋升候选 CAD 为结构资产 |

## 8. `/api/query` 主响应结构

前端重构时，最重要的接口是 `/api/query`。它是一切页面状态的源头。

请求结构来源：`backend/app/schemas.py -> QueryRequest`

```json
{
  "text": "离心泵机械密封持续滴漏，现场人员想直接拆卸端盖。",
  "equipment": "pump",
  "model": "ISG80-160",
  "maintenance_level": "二级检修",
  "image_caption": "泵端机械密封区域有液体滴漏和油污。",
  "visual_asset_id": 1,
  "top_k": 6
}
```

关键响应字段：

```json
{
  "diagnosis": "...",
  "possible_causes": [],
  "sop_steps": [],
  "tools_and_parts": [],
  "acceptance": [],
  "risk_level": "high|medium|low",
  "compliance": [],
  "citations": [],
  "similar_cases": [],
  "visual_analysis": {},
  "graph_paths": [],
  "visual_evidence": [],
  "spatial_guidance": {},
  "workflow_state": {},
  "tri_mro_alignment": {},
  "claim_cards": [],
  "primary_claim_card": {},
  "resource_verification_summary": {},
  "agents": []
}
```

UI 应优先使用：

1. `primary_claim_card`
2. `workflow_state`
3. `spatial_guidance`
4. `citations`
5. `similar_cases`
6. `graph_paths`

`agents` 和 `model_review` 更适合放在详情/调试区域。

## 9. 推荐主线演示数据

结构化测试数据文件：`data/demo/tri_mro_test_cases.json`

黄金样例：

| 编号 | 设备 | 输入摘要 | 目标部件 |
| --- | --- | --- | --- |
| G01 | 电机 | 电机运行 30 分钟后轴承端温升、振动、异响 | `motor.bearing` |
| G02 | 离心泵 | 机械密封持续滴漏，现场想直接拆卸端盖 | `pump.mechanical_seal` |
| G03 | 轴承 | 外圈滚道磨损、疑似剥落 | `bearing.outer_ring` / `bearing.rolling_elements` |
| G04 | 发动机 | 冷车起动困难，火花塞积碳，检查间隙和压缩压力 | `engine.spark_plug` |

反例样例：

| 编号 | 场景 | UI 应体现 |
| --- | --- | --- |
| A01 | 证据不足 | 拒答/降级/人工复核 |
| A02 | 用户要求直接拆卸 | Safety Gate 阻断 |
| A03 | 文本图片冲突 | 冲突检测，人工复核 |
| A04 | 不支持设备 | 不高置信回答 |
| A05 | 云模型失败 | fallback 可用 |
| A06 | 错误案例入库 | 审核或人工拦截 |
| A07 | CAD 无精确锚点 | 显示绑定等级和人工校准 |
| A08 | 绕过安全确认 | 后端不放行 |

最推荐主演示：G02 离心泵机械密封泄漏。

## 10. 视觉设计方向

建议整体风格：工业检修控制台，不要做成 AI 聊天页面，也不要做成营销落地页。

关键词：

```text
工程化
证据清楚
状态明确
层级克制
高风险强提示
可审计
少装饰
强任务流
```

### 10.1 信息层级

优先级从高到低：

1. 当前任务状态
2. Claim Card 判断
3. Safety Gate 是否阻断
4. 当前定位部件
5. SOP 下一步
6. 证据链
7. 案例沉淀
8. 评测与资源
9. 模型路由、候选 CAD、开发工具

### 10.2 颜色建议

不要使用单一蓝紫渐变风格。建议以工业中性色为主，少量状态色。

| 用途 | 建议 |
| --- | --- |
| 背景 | 浅灰、白、低饱和冷灰 |
| 主色 | 深青、墨绿、工业蓝任选一种 |
| 成功 | 绿色 |
| 需要确认 | 琥珀色 |
| 阻断/危险 | 红色 |
| 证据/引用 | 蓝灰 |
| CAD/结构 | 青色或钢蓝 |

### 10.3 组件建议

- Claim Card：主卡片，显示证据分、置信等级和关键链路。
- Safety Gate：状态机卡片，红/黄/绿明确。
- Evidence Drawer：引用证据抽屉，不要首屏堆满。
- Component Contract：部件契约侧栏。
- SOP Timeline：步骤时间线，每步绑定风险和部件。
- CAD Viewer：中间大视窗，右侧证据，底部步骤。
- Knowledge Pipeline：横向流程条，显示审核和写入状态。
- Metrics Board：少量关键指标卡，不要堆所有测试明细。

## 11. 当前功能复杂度分层

为了避免继续“杂乱”，建议把功能分为三层。

### 11.1 主线功能，必须首屏可见

- 设备/型号/故障/图片输入
- Claim Card
- Evidence Budget
- Safety Gate
- SOP 下一步
- CAD 部件定位入口
- 从当前任务生成案例

### 11.2 重要支撑功能，可放二级详情

- 手册引用详情
- 相似案例详情
- 图谱路径详情
- FMEA Risk Chain
- 人工修正
- Knowledge Write Pipeline
- 评测指标

### 11.3 高级/实验功能，默认折叠

- 模型探测
- 入库手册
- 重建索引
- 生成样例
- 候选 CAD 资产池
- photo-to-CAD / photo-to-3D
- 零件树候选资源
- FreeCAD/Blender/OpenSCAD runtime

## 12. 页面重构优先级

### P0：先重构主体验

1. 检修任务页
2. Claim Card 主结果
3. Safety Gate 阻断展示
4. CAD 工位基础布局
5. 从任务生成案例

### P1：再整理证据和评测

1. 引用证据抽屉
2. 当前任务证据链图谱
3. Knowledge Write Pipeline
4. Innovation Metrics

### P2：最后处理高级工具

1. 候选 CAD
2. 模型路由
3. 资源入库
4. 零件树候选
5. photo-to-CAD 实验链路

## 13. 需要避免的 UI 表达

不要这样表达：

- “系统能自动维修设备”
- “CAD 面级精确定位”
- “photo-to-3D 可用于安全放行”
- “所有知识都已权威审核”
- “外部模型一定在线可用”

推荐这样表达：

- “系统提供检修辅助判断，关键步骤需人工复核”
- “当前为部件级/锚点级/语义热点绑定”
- “photo-to-CAD/photo-to-3D 为实验链路，不用于尺寸测量和安全放行”
- “案例经审核后进入知识库”
- “云模型失败时使用缓存和本地规则 fallback”

## 14. 当前已知限制

这些限制应在 UI 或答辩材料中诚实标注。

| 限制 | 当前状态 | UI 表达建议 |
| --- | --- | --- |
| LoongArch 实机 | 未提供目标环境时无法验证 | 显示“待目标环境验收” |
| CAD 面级绑定 | 当前不主打 | 显示“语义热点/锚点级” |
| 泵/电机/发动机热点 | 部分靠语义或 sidecar | 提供人工校准入口 |
| photo-to-CAD | 实验链路 | 默认折叠 |
| 真实回滚 API | 目前主要记录 rollback_id | 不显示成已实现一键回滚 |
| 角色权限系统 | 当前未完整实现 | 审核权限不要夸大 |
| 引用真实性 | 自动化只能检测字段，仍需人工审阅 | 设计“待审核/已审核”标记 |

## 15. 当前测试状态

最新完整测试输出：

- `test-results/tri-mro-full-test-execution.json`
- `test-results/tri-mro-full-test-execution.md`
- `test-results/system-smoke-report.md`

最近一次结果摘要：

```text
完整测试项：68
通过：54
失败：0
自动化通过：53
browser smoke：通过
全量 pytest：105 passed
```

仍需人工/环境验证：

- 人工引用真实性审阅
- CAD 热点人工校准
- 错误案例污染拦截
- LoongArch + 银河麒麟目标环境
- 角色权限和真实回滚 API

## 16. 重构人员最小理解路径

如果设计师或前端只看最少文件，建议按顺序看：

1. 本文件：`docs/UI_REDESIGN_BRIEF.md`
2. 当前前端：`frontend/index.html`
3. 当前交互逻辑：`frontend/app.js`
4. 主接口：`backend/app/main.py` 的 `/api/query`
5. 判断卡：`backend/app/claim_card.py`
6. 部件契约：`backend/app/component_contracts.py`
7. 安全闸门：`backend/app/safety_gate.py`
8. 工作流状态：`backend/app/workflow.py`
9. 测试用例：`data/demo/tri_mro_test_cases.json`

## 17. 建议的新页面线框

### 17.1 检修任务页

```text
┌────────────────────────────────────────────────────────────┐
│ 全局任务条：设备 / 型号 / component_key / 证据分 / 安全状态 │
├───────────────┬──────────────────────────────┬─────────────┤
│ 现场输入       │ Claim Card 主判断             │ 下一步动作     │
│ 设备类型       │ 故障判断                       │ 进入结构工位   │
│ 型号           │ Evidence Budget                │ 查看作业票     │
│ 检修等级       │ 三链对齐摘要                    │ 生成案例       │
│ 故障文本       │ Safety Gate 摘要                │ 人工修正       │
│ 图片上传       │ 证据缺口/复核策略               │               │
├───────────────┴──────────────────────────────┴─────────────┤
│ 证据详情抽屉：手册 / 案例 / 图谱 / 视觉 / Agent trace        │
└────────────────────────────────────────────────────────────┘
```

### 17.2 结构工位页

```text
┌────────────────────────────────────────────────────────────┐
│ 当前任务条：泵 / ISG80-160 / pump.mechanical_seal / BLOCKED │
├──────────────┬───────────────────────────────┬─────────────┤
│ 部件候选      │ 3D GLB 主视窗                  │ 部件契约       │
│ 设备切换      │ 模型旋转/缩放/聚焦              │ 视觉线索       │
│ 图片线索      │ 热点/锚点                       │ 安全门         │
│ 绑定等级      │                                │ SOP 当前步     │
├──────────────┴───────────────────────────────┴─────────────┤
│ SOP 时间线：安全确认 → 拆检 → 检查 → 判定 → 验收             │
└────────────────────────────────────────────────────────────┘
```

### 17.3 作业票与安全页

```text
┌────────────────────────────────────────────────────────────┐
│ 作业票标题 / 风险等级 / 当前状态 BLOCKED                   │
├───────────────────────┬────────────────────────────────────┤
│ SOP 步骤列表           │ Safety Gate                         │
│ #1 安全确认            │ 缺失：断电、泄压、PPE                 │
│ #2 清理泄漏区域        │ 审计日志                              │
│ #3 拆卸密封端盖        │ 确认按钮 / 转人工复核                  │
│ #4 检查密封端面        │                                      │
├───────────────────────┴────────────────────────────────────┤
│ 工具备件 / 验收标准 / 引用证据                              │
└────────────────────────────────────────────────────────────┘
```

### 17.4 知识沉淀页

```text
┌────────────────────────────────────────────────────────────┐
│ 从当前任务生成案例：Claim Card → 案例草稿                  │
├──────────────┬──────────────────────┬──────────────────────┤
│ 案例表单      │ 待审核列表             │ 写入流水线             │
│ 设备/故障     │ pending_review         │ 审核 → 图谱 → 索引     │
│ 原因/措施     │ approved/rejected      │ 回滚号 / 影响范围      │
└──────────────┴──────────────────────┴──────────────────────┘
```

## 18. 给 UI 设计的最终目标

重构后的 UI 应该让评委在 30 秒内看懂：

1. 这是一个检修作业系统，不是聊天机器人。
2. 当前任务是什么设备、什么故障、哪个部件。
3. 系统为什么这样判断，有哪些证据。
4. 需要修哪里，CAD/部件如何定位。
5. 下一步怎么修，是否被安全闸门阻断。
6. 修完以后如何沉淀成知识。
7. 系统如何证明自己比普通 RAG 更可信。

最终页面不应该追求功能全露出，而应该围绕一句话组织：

> 让每个检修判断有证据、能定位、可执行、可阻断、可沉淀。
