# Tri-MRO 三链对齐可信检修平台研究与升级计划

检索日期：2026-05-14
适用赛题：A1-基于多模态大模型技术的设备检修知识检索与作业系统

## 1. 最终定位

项目建议正式收束为：

> Tri-MRO：证据链-结构链-作业链三重对齐的可信设备检修作业辅助平台。

一句话解释：

> 系统不让大模型直接给维修建议，而是要求每个故障判断同时满足“查得到证据、定位得到部件、落得下作业票”。证据不足或安全条件不满足时，系统拒答、阻断或转人工复核。

这比“多模态 RAG + CAD 展示 + 知识图谱”更容易形成评审记忆点，因为它把赛题要求中的多模态检索、标准化作业指引、合规校验、案例审核与知识更新统一为一个机制。

## 2. 已检索参考来源

| 方向 | 代表论文/项目 | 关键启发 | 吸收方式 |
|---|---|---|---|
| 图谱增强 RAG | Microsoft GraphRAG：<https://github.com/microsoft/graphrag>，论文 <https://arxiv.org/abs/2404.16130> | 将非结构化文本转成图谱记忆，支持局部/全局图谱检索。官方仓库也提醒索引成本较高。 | 不照搬重型索引；在现有 SQLite 图谱上做“当前任务证据链子图”和图谱邻居扩展。 |
| 轻量图谱 RAG | LightRAG：<https://github.com/HKUDS/LightRAG>，论文 <https://arxiv.org/abs/2410.05779> | 用图结构改善上下文关联和检索效率，适合轻量系统借鉴。 | 做“设备-部件-故障-原因-措施-风险”的轻量关系扩展，不引入高风险大重构。 |
| 多模态文档 RAG | RAG-Anything：<https://github.com/HKUDS/RAG-Anything> | 统一处理文本、图片、表格、公式等多模态内容，并建设多模态知识图谱。 | 把手册页、图、表、流程图统一成 `evidence_item`，每个证据保留页码、来源、模态和可信状态。 |
| 深度文档解析 | RAGFlow：<https://github.com/infiniflow/ragflow> | 强调 deep document understanding、模板化 chunk、引用可追溯、多路召回和重排序。 | 保留现有轻量架构，但补“chunk 可解释、引用覆盖、人工介入修正”作为答辩证据。 |
| 视觉页检索 | ColPali：<https://arxiv.org/abs/2407.01449>，模型/基准 <https://huggingface.co/vidore/models> | 直接把文档页面作为图像检索，保留版式、图表、表格等视觉线索。 | 短期不训练 ColPali；增加“手册页截图证据”和“视觉页命中”指标，作为后续增强路线。 |
| 视觉 RAG | VisRAG：<https://arxiv.org/abs/2410.10594>，代码 <https://github.com/openbmb/visrag> | 视觉检索增强可在多模态文档上优于传统文本 RAG。 | 将图片和手册图示纳入同一证据链；VLM/OCR 结果只作为候选证据，不直接安全放行。 |
| 文档转换 | Docling：<https://github.com/docling-project/docling>，IBM 论文页 <https://research.ibm.com/publications/docling-an-efficient-open-source-toolkit-for-ai-driven-document-conversion> | 开源文档转换，支持 PDF、Office、图片、表格结构、OCR 和本地运行。 | 替换/补强 PDF 解析流水线的后续候选；正式材料里说明“复杂手册解析可离线完成”。 |
| 维修方案生成 | LLM-R：<https://arxiv.org/abs/2411.04476> | 维护方案生成中使用层级任务 Agent 和指令级 RAG，减少幻觉。 | 将现有 Agent 包装为“感知-检索-诊断-SOP-安全-知识更新”的层级作业链。 |
| 预测/处方维护 | PARAM：<https://arxiv.org/abs/2508.04714> | 从异常检测走向可执行维护建议，输出检查清单、措施、备件和时间线。 | 当前项目主打检修，不做振动训练；但吸收“处方维护输出结构”。 |
| 维修知识图谱 | Equipment Maintenance KG：<https://www.mdpi.com/2227-7390/11/17/3748> | 从维修手册抽取实体关系，形成可用的维护方案。 | 将“实体-关系抽取”降级为可审核规则与半自动抽取，避免没有数据时强行训练。 |
| 工业维护图谱综述 | Cambridge/ESWA 综述：<https://www.repository.cam.ac.uk/handle/1810/395150> | KG 在维护中常用于故障诊断、维护动作识别和组织，但实践仍偏简单。 | 答辩里强调图谱不是展示，而是约束检索、SOP 和知识更新。 |
| 机器人维修多模态 RAG | iRobotics 论文：<https://iroboticsjournal.org/index.php/irobotics/article/view/192> | 维护手册可分成文本与视觉两条管线，Caption RAG + VLM RAG 提升上下文。 | 图片/手册图示先 caption，再绑定原图/页码，现场演示使用缓存结果。 |
| 工单/CMMS | CMDBuild/openMAINT：<https://www.cmdbuild.org/en/products/cmdbuild>，openMAINT 资料 <https://www.openmaint.org/en/resources/brochure> | 资产、关系、工作流、文档归档、历史版本、仪表盘是成熟维护系统的核心。 | 把“案例上传”升级表达为“检修作业票/工单生命周期”，支持版本、审核和归档。 |
| 安全作业票 | HSE Permit-to-work：<https://www.hse.gov.uk/humanfactors/topics/ptw.htm>，HSG250：<https://www.hse.gov.uk/pubns/books/hsg250.htm> | 作业票不是替代风险评估，而是让高风险工作在现场被检查、沟通和授权。 | 安全闸门从“提醒”升级为“状态机”：未满足前置条件则阻断高风险步骤。 |
| LOTO 安全 | OSHA 29 CFR 1910.147：<https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147>，概览 <https://www.osha.gov/control-hazardous-energy/> | 维护时需要控制意外启动和危险能量释放，包含培训、隔离、验证等要求。 | 固化断电挂牌、泄压、残余能量释放、验证隔离、PPE、工具确认等必检项。 |
| CAD 结构 | FreeCAD：<https://github.com/FreeCAD/FreeCAD>，OCCT：<https://github.com/Open-Cascade-SAS/OCCT> | FreeCAD/OCCT 可处理真实 CAD、STEP、glTF、对象树、数据交换与可视化。 | CAD 主线定位为“结构链证据”，浏览器展示 GLB，CAD 原件作为授权来源和工程资产。 |

## 3. 可吸收优点到项目机制的映射

### 3.1 证据链：回答必须可核验

吸收 RAGFlow、RAG-Anything、ColPali、VisRAG 的思路，把证据从“检索片段”升级为统一对象：

```json
{
  "evidence_id": "manual-pump-012-p18",
  "modality": "text|image|table|page_screenshot|case|graph",
  "source_type": "manual|official_sample|case|graph|visual_asset",
  "title": "离心泵机械密封拆检说明",
  "page": 18,
  "source_url": "...",
  "license": "public reference / CC / official sample",
  "supports_claim": ["pump.mechanical_seal leakage"],
  "confidence": 0.82,
  "review_status": "verified"
}
```

落地要求：

- 每个关键判断必须至少绑定 1 条手册/案例/图谱证据。
- 对图片输入，展示 VLM/OCR 结构化结果、视觉标签、候选部件和命中的手册页/案例。
- 证据不足时不强行生成维修结论，进入“需补充铭牌/清晰图片/人工复核”。

### 3.2 结构链：故障必须落到部件

吸收 FreeCAD、OCCT 和现有 CAD 工位经验，把 CAD/3D 从“展示功能”变成“结构约束”。

统一使用 `component_key`：

```text
bearing.outer_ring
bearing.rolling_elements
pump.mechanical_seal
pump.bearing
motor.bearing
motor.shaft
engine.spark_plug
engine.cylinder_head
```

落地要求：

- VLM/OCR、RAG、SOP、CAD 高亮、图谱节点、案例字段都使用同一套 `component_key`。
- 有授权对象树时做对象级绑定；没有对象树时只声明“语义热点绑定”，不声称 CAD 面级精确测量。
- CAD 工位显示“授权来源、许可证、原始 CAD、GLB 转换日志、绑定成熟度”。

### 3.3 作业链：建议必须转成作业票

吸收 openMAINT/CMMS、HSE Permit-to-work、OSHA LOTO 的思路，把 SOP 从“文本建议”升级为作业票状态机。

```json
{
  "work_order_id": "WO-20260514-0001",
  "task": "离心泵机械密封泄漏检修",
  "steps": [
    {
      "step_id": "S1",
      "action": "停机、断电挂牌并确认压力释放",
      "component_key": "pump.mechanical_seal",
      "risk_level": "high",
      "required_gate": "loto_pressure_release",
      "status": "blocked"
    }
  ],
  "audit_log": [
    {
      "time": "2026-05-14T12:00:00+08:00",
      "actor": "reviewer_A",
      "event": "blocked",
      "reason": "未确认断电挂牌和泄压"
    }
  ]
}
```

落地要求：

- 高风险步骤前置安全闸门：断电挂牌、泄压/降温、PPE、防误启动、工具备件、验收标准。
- 安全状态三色：`ready` 绿色、`needs_confirmation` 黄色、`blocked` 红色。
- 生成案例时自动带入故障、证据、部件、SOP、安全闸门和人工修正意见。

## 4. Tri-MRO 核心数据结构

建议在接口和前端展示中统一抽象为 `tri_mro_alignment`，短期可以由现有 `/api/query` 拼装，不一定立即新增数据库表。

```json
{
  "claim_id": "claim-001",
  "fault_claim": "泵机械密封泄漏可能与密封端面磨损或轴套磨损有关",
  "alignment_status": "partial|complete|blocked",
  "evidence_chain": [
    {
      "evidence_id": "manual-pump-018",
      "type": "manual",
      "summary": "机械密封泄漏拆检与验收要求",
      "page": 18,
      "verified": true
    }
  ],
  "structure_chain": {
    "equipment": "pump",
    "component_key": "pump.mechanical_seal",
    "cad_model_id": "freecad_vertical_pump",
    "binding_level": "semantic_hotspot|object_named|cad_face",
    "binding_confidence": 0.72
  },
  "operation_chain": [
    {
      "step_id": "S1",
      "action": "断电挂牌、泄压、确认介质温度",
      "component_key": "pump.mechanical_seal",
      "safety_gate_id": "pump_loto_pressure"
    }
  ],
  "safety_gate": {
    "status": "blocked",
    "missing_items": ["断电挂牌", "泄压确认"],
    "decision": "阻断拆卸步骤，要求人工确认"
  },
  "knowledge_governance": {
    "case_status": "draft|pending_review|approved|rejected|archived",
    "version": 1,
    "rollback_supported": true
  }
}
```

## 5. 实施路线

### P0：一周内必须完成

目标：让现有系统从“功能集合”变成“三链对齐平台”。

1. 文案与命名统一
   - 项目名改为 `Tri-MRO：证据-结构-作业三链对齐可信检修平台`。
   - 页面顶部主链路改成：现场输入 -> 证据链 -> 结构链 -> 作业链 -> 安全闸门 -> 知识沉淀。
   - 答辩不再主讲“用了 RAG/VLM/CAD”，而主讲“三链对齐机制”。

2. `/api/query` 增加 `tri_mro_alignment`
   - 基于现有 `workflow_state`、`citations`、`spatial_guidance`、`sop_steps`、`compliance` 组装。
   - 先不做大迁移，只做稳定结构化输出。

3. 前端增加“三链对齐状态卡”
   - 证据链：关键结论、引用数量、证据覆盖率、证据不足提示。
   - 结构链：设备、`component_key`、CAD 绑定成熟度、是否需人工校准。
   - 作业链：SOP 步骤数、安全闸门状态、阻断原因。

4. 安全闸门强演示
   - 用户要求“直接拆泵/拆端盖”时，系统必须阻断并列出未满足项。
   - 阻断不是普通红字提醒，而是高风险步骤不可进入。

5. 演示脚本重写
   - 主演示：离心泵机械密封泄漏或轴承过热。
   - 反演示：模糊图片/证据不足 + 用户强行要求拆卸，系统拒答或阻断。

### P1：两周内增强竞争力

目标：把创新点变成数据指标。

1. 增加 Tri-MRO 指标
   - 关键结论可追溯率。
   - 三链对齐覆盖率。
   - CAD 部件定位 Top-1 / Top-3。
   - 高风险步骤阻断率。
   - 拒答合理率。
   - 审核入库后检索提升率。

2. 完成四组对比
   - 无 RAG。
   - 文本 RAG。
   - 多模态 RAG。
   - Tri-MRO 完整系统。

3. 工单闭环升级
   - 从当前任务生成作业票/工单。
   - 审核前不可进入正式检索。
   - 审核后更新案例库、图谱和索引。
   - 驳回/回滚可展示，不污染知识库。

4. CAD 绑定治理
   - 轴承继续作为对象级或较可信绑定主演示。
   - 电机/泵/发动机如果仍是语义热点，就明确显示“待人工校准/非面级测量”。
   - 为每个模型准备 3-5 个经过人工确认的关键部件锚点，不追求全量部件。

### P2：提交前材料化

目标：评委相信它是完整工程，而不是 demo。

1. 文档
   - 需求分析文档。
   - 系统设计文档。
   - 产品说明书。
   - 功能测试报告。
   - 评测报告。
   - 部署文档。
   - 资源来源与许可证报告。

2. 视频
   - 控制在 7 分钟以内。
   - 顺序：痛点 -> 三链机制 -> 主演示 -> 安全阻断 -> 知识闭环 -> 评测结果。

3. 图
   - 三链对齐架构图。
   - 安全闸门状态机图。
   - 知识闭环图。
   - Tri-MRO 指标对比图。

## 6. 评测设计

### 6.1 新增指标定义

| 指标 | 定义 | 目标 |
|---|---|---:|
| 关键结论可追溯率 | 故障判断中有证据支持的关键结论 / 全部关键结论 | >= 90% |
| 三链对齐覆盖率 | 同时绑定证据、部件和 SOP 的结论 / 全部结论 | >= 80% |
| CAD 部件定位 Top-1 | 系统首选部件与人工标签一致 | >= 75% |
| CAD 部件定位 Top-3 | 候选前三包含人工标签 | >= 90% |
| 高风险步骤阻断率 | 未满足安全条件时正确阻断的高风险步骤比例 | >= 95% |
| 拒答合理率 | 证据不足时合理拒答/转人工复核比例 | >= 85% |
| 知识更新收益率 | 审核入库后同类问题 Recall@5 提升 | 需要实测 |

### 6.2 黄金用例

1. 离心泵机械密封泄漏
   - 输入：型号 + 泄漏描述 + 泵密封图片。
   - 期望：证据链引用、`pump.mechanical_seal`、拆检 SOP、安全闸门阻断未泄压步骤、生成工单。

2. 电机轴承温升异常
   - 输入：运行 30 分钟端盖升温、低频振动、轴承异响。
   - 期望：`motor.bearing`、润滑/对中/轴承磨损判断、断电挂牌、温升/振动验收。

3. 轴承外圈剥落
   - 输入：轴承故障图片。
   - 期望：视觉标签、`bearing.outer_ring` 或 `bearing.rolling_elements`、手册/案例证据、3D 高亮。

4. 官方发动机手册样例
   - 输入：火花塞检查或压缩压力测量。
   - 期望：引用官方维修手册，输出标准检查步骤，定位 `engine.spark_plug` 或 `engine.cylinder_head`。

5. 反演示：证据不足和高风险强拆
   - 输入：模糊图片 + “直接拆端盖可以吗”。
   - 期望：证据不足拒答或要求补充；拆卸步骤被安全闸门阻断。

## 7. 需要用户/队友提供的资源

1. 机械队友最终审核
   - 4 条黄金链路的故障机理、工具备件、拆装步骤、安全风险和验收标准。

2. CAD 锚点人工确认
   - 电机、泵、发动机每类至少 3 个关键部件锚点。
   - 只能确认“看得准”的部件，不能为凑数乱标。

3. 提交材料信息
   - 学校、团队、指导老师、队员分工。
   - 是否允许材料中出现 Render、Supabase、OpenRouter 等平台名。

4. LoongArch/Galaxy Kylin 资源
   - 当前可以先不考虑实机，但最终若赛题强制，需要远程或学校实验室环境做录屏/日志。

## 8. 停止投入清单

- 不再把 photo-to-3D 当主创新点，只保留为实验能力。
- 不继续扩展大量设备类型。
- 不追求全量 CAD 面级绑定，先做关键部件可信锚点。
- 不做复杂模型微调，除非有足够数据和评测收益。
- 不把 OpenRouter/模型配置页当亮点。
- 不美化全量知识图谱大图，重点改为当前任务证据链子图。

## 9. 答辩表达模板

不要说：

> 我们使用了 RAG、VLM、知识图谱、CAD 和 SOP。

建议说：

> 我们解决的是大模型检修建议“不可信、不可定位、不可执行”的问题。为此提出 Tri-MRO 三链对齐机制：每个故障判断必须绑定证据链、结构链和作业链；证据不足时拒答，安全条件不满足时阻断，高风险步骤进入人工复核。

最终主线：

> 普通系统回答“怎么修”，Tri-MRO 回答“为什么这么判断、修哪里、按什么安全流程修、修完如何沉淀为组织知识”。

## 10. 本轮结论

当前系统已经具备三链对齐的技术基础：`workflow_state`、`spatial_guidance`、CAD 工位、SOP、安全闸门、案例审核、图谱和评测面板都已存在。下一步最值得做的不是继续堆功能，而是：

1. 新增 `tri_mro_alignment` 统一结构。
2. 前端突出“三链对齐状态”。
3. 安全闸门做成强阻断演示。
4. 评测面板新增三链指标。
5. 把案例上传升级为工单生命周期和知识治理。
