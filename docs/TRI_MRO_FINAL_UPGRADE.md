# Tri-MRO 最终版升级说明

## 定位

Tri-MRO 最终版将系统收束为“证据治理型检修作业控制系统”。核心表达是：

> 用证据约束判断，用结构约束定位，用安全闸门约束作业，用审核机制约束知识更新。

系统不再把 RAG、VLM、CAD、SOP、图谱作为散装功能展示，而是统一到四个可审计对象：

- `Claim Card`：检修判断卡，负责关键结论的证据链、结构链、作业链对齐。
- `Component Contract`：部件知识契约，统一 OCR/VLM、RAG、CAD、图谱、SOP、案例中的 `component_key`。
- `Safety Gate`：安全闸门状态机，将高风险作业从“提醒”升级为“阻断/放行/复核”。
- `Knowledge Write Pipeline`：知识写入流水线，保证案例审核后才进入案例库、图谱和索引。

## 已落地机制

### Claim Card

`/api/query` 返回 `claim_cards` 与 `primary_claim_card`。判断卡包含：

- 故障判断与置信等级
- `Evidence Budget` 证据预算
- 手册/案例/图谱/视觉证据链
- CAD/部件结构链
- SOP 作业链
- FMEA 风险链
- Safety Gate 状态
- 人工复核策略

证据不足时，系统不会给出确定结论，只输出排查方向、补充采集建议或人工复核建议。

### Component Contract

核心部件已升级为契约对象，覆盖：

- `pump.mechanical_seal`
- `pump.bearing`
- `bearing.outer_ring`
- `bearing.rolling_elements`
- `motor.bearing`
- `motor.shaft`
- `engine.spark_plug`
- `engine.cylinder_head`

契约字段包括别名、常见故障、视觉线索、手册关键词、CAD 绑定等级、安全风险和必需安全门。

当前泵、电机、发动机模型的结构绑定明确标注为“语义热点/锚点级”，需人工校准，不声称 CAD 面级或尺寸级绑定。

### Safety Gate

状态机包含：

- `DRAFT`
- `WAITING_SAFETY_CHECK`
- `BLOCKED`
- `READY`
- `IN_PROGRESS`
- `NEED_REVIEW`
- `COMPLETED`
- `ARCHIVED`

高风险步骤若未确认断电挂牌、泄压、温度、PPE、工具等条件，会进入 `BLOCKED`。阻断、确认、放行记录进入审计轨迹，供案例沉淀和答辩展示。

### Evidence Budget

证据分按四类来源计算：

```text
evidence_score =
0.35 * manual_score
+ 0.25 * case_score
+ 0.20 * graph_score
+ 0.20 * visual_score
```

行为阈值：

- `>= 0.75`：可输出明确判断
- `0.50 - 0.75`：可能判断，需要人工确认
- `0.30 - 0.50`：仅给排查方向
- `< 0.30`：拒绝确定结论，要求补充铭牌、清晰图片或工况信息

### FMEA Risk Chain

系统采用轻量 FMEA 思路，不声称完全符合 IEC/AIAG/VDA 标准全文。每个黄金案例输出：

- 故障模式
- 可能原因
- 影响后果
- 严重度、发生度、探测度
- RPN
- 推荐处理动作

### Knowledge Write Pipeline

案例审核通过后返回知识写入结果：

- 影响部件
- 图谱更新
- 索引更新
- 回滚号
- 回归评测结果
- 审计记录

审核前案例不进入正式检索；驳回案例不写入图谱和索引。

### Innovation Metrics

`/api/metrics` 新增 `tri_mro_innovation_metrics`：

- 关键结论可追溯率
- 三链对齐覆盖率
- CAD 部件定位 Top-1 / Top-3
- 高风险步骤阻断率
- 拒答合理率
- 知识更新后召回提升率
- 知识污染拦截率

这些指标直接绑定 Claim Card、Safety Gate 和 Knowledge Write Pipeline。

## 外部资源状态

本阶段新增外部资料只作为规则设计依据，不下载或打包受版权限制全文。

| 资源 | 用途 | 状态 |
| --- | --- | --- |
| OSHA Control of Hazardous Energy | 断电挂牌、危险能量控制、安全闸门规则依据 | 官方网页可访问，仅保存 URL 和摘要 |
| OSHA 29 CFR 1910.147 | LOTO 标准条文参考 | 官方网页可访问，仅保存 URL 和摘要 |
| HSE HSG250 Permit-to-work systems | 作业许可、审核、风险评估、审计思想参考 | 页面显示可免费下载；CLI 下载曾遇到 TLS EOF，当前不强制下载 PDF |
| IEC 60812:2018 | FMEA/FMECA 方法官方简介 | 付费标准，仅引用官方简介，不保存正文 |
| AIAG & VDA FMEA Handbook | 汽车行业 FMEA 实践参考 | 付费/授权资料，仅引用官方产品页，不保存正文 |

## 主演示建议

主链路应固定为：

```text
离心泵机械密封泄漏
→ 图片/文本输入
→ Evidence Budget 判断证据是否足够
→ Claim Card 输出故障判断
→ Component Contract 定位 pump.mechanical_seal
→ CAD 工位展示语义热点和人工校准边界
→ Safety Gate 阻断未断电/未泄压拆检
→ 确认安全门后放行
→ 从当前任务生成案例
→ 人工审核入库
→ Knowledge Write Pipeline 更新图谱和索引
→ Innovation Metrics 展示优势
```

反演示应固定为：

```text
证据不足/图片模糊/型号未知
→ Evidence Budget 低分
→ Claim Card 不给确定结论
→ 要求补充铭牌、清晰图片、工况信息
→ 用户要求直接拆卸时 Safety Gate 阻断
```

## 可信边界

- photo-to-CAD/photo-to-3D 仍为实验链路，不作为安全放行依据。
- CAD 当前以部件级、锚点级和语义热点为主，不声称完整面级绑定。
- FMEA 为轻量风险链，不替代企业正式 FMEA 流程。
- 外部安全/FMEA 资料只用于设计启发，项目提交包不包含未授权全文。
