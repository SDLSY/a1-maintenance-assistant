# Tri-MRO 工作台完整 UI 设计套图 V2

## 目的

这一版用于后续重构 Tri-MRO 工作台页面，不是单张 demo 图，也不是宣传页草图。设计目标是把系统做成一个可实际使用的“可信设备检修作业控制平台”，覆盖从任务创建到检修执行、证据复核、CAD 定位、作业票、安全闸门、知识写入、评测证明和交付材料的完整产品链路。

输出目录：

`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\workbench_design_suite_v2`

总览图：

`D:\30726\Desktop\竞赛目录\a1-maintenance-assistant\materials\workbench_design_suite_v2\workbench-design-suite-v2-contact-sheet.png`

## 总体产品框架

Tri-MRO 工作台按“检修任务生命周期”组织，而不是按技术组件堆叠：

1. 总览与任务队列
2. 检修任务台
3. 图片识别与 OCR/VLM 详情
4. Claim Card 检修判断卡
5. 证据链图谱
6. 手册证据与相似案例
7. 证据不足/冲突复核
8. CAD 结构工位
9. CAD 锚点人工校准
10. CAD/GLB 资产详情
11. 作业票与 Safety Gate
12. 案例草稿与审核
13. 知识写入、回滚与再评测
14. 评测证明与失败分析
15. 资源验证与系统管理
16. 现场平板端和手机复核端
17. 报告导出与答辩材料

## 全局风格提示词

```text
Design a professional Chinese industrial SaaS workbench UI for “Tri-MRO”, a trustworthy equipment maintenance operation control platform.

Tri-MRO is not a chatbot and not a decorative CAD viewer. It converts a field maintenance task into a controlled workflow:
现场输入 → OCR/VLM 现场感知 → 证据检索 → Claim Card 检修判断卡 → CAD/部件结构定位 → SOP 作业票 → Safety Gate 安全闸门 → 案例沉淀 → 人工审核 → 图谱/索引更新 → 评测证明.

Visual style:
- Industrial maintenance control console
- Enterprise B2B SaaS, dense but readable
- Light gray background, white panels, subtle borders
- Deep teal and steel blue primary color
- Red for BLOCKED, amber for NEED_REVIEW, green for READY
- Left sidebar + top global task strip + main workspace
- Chinese UI labels
- Focus on trust, evidence, structure, operation and safety

Core components:
- Global task status strip
- Claim Card
- Evidence Budget
- Evidence Chain
- Structure Chain
- Operation Chain
- Component Contract
- CAD/GLB Viewer
- SOP Timeline
- Safety Gate state machine
- Knowledge Write Pipeline
- Innovation Metrics
```

## 负面约束提示词

```text
Do not design a chatbot-first interface.
Do not use robot mascots, purple AI gradients, abstract glowing blobs, or dark cyberpunk style.
Do not claim CAD face-level precision when the binding is semantic hotspot or component-level.
Do not imply photo-to-CAD can be used for safety approval.
Do not make Safety Gate just a reminder; it must look like a blocking control mechanism.
Do not make unreviewed cases look already written into the formal knowledge base.
Do not make debugging/model-routing tools visually dominant.
Do not overcrowd the first screen with all citations and logs.
```

## 页面清单

| 编号 | 文件 | 用途 |
| --- | --- | --- |
| 00 | `00-design-system-shell.png` | 设计系统、应用壳层、导航、状态色、核心组件规范 |
| 01 | `01-overview-task-queue.png` | 工作台首页、任务队列、风险概览、待办入口 |
| 02 | `02-task-new-empty.png` | 新建检修任务、空状态、输入校验、图片上传 |
| 03 | `03-task-generating-agent-progress.png` | 生成中状态、Agent 实时进度、消息传递动画参考 |
| 04 | `04-task-result.png` | 检修任务生成结果、Claim Card 摘要、下一步动作 |
| 05 | `05-vision-ocr-detail.png` | 图片识别、OCR/VLM、视觉证据、部件候选 |
| 06 | `06-claim-card-list.png` | Claim Card 列表、筛选、批量复核 |
| 07 | `07-claim-card-review-detail.png` | Claim Card 详情、证据预算、审核决策 |
| 08 | `08-evidence-graph.png` | 当前任务证据链图谱，不展示全量混乱图 |
| 09 | `09-manual-citation-detail.png` | 手册引用详情、页码、来源、验证信息 |
| 10 | `10-case-library-detail.png` | 相似案例库、案例详情、相似度解释 |
| 11 | `11-insufficient-conflict-review.png` | 证据不足、文本图片冲突、人工复核 |
| 12 | `12-cad-structure-main.png` | CAD 结构工位主页面、部件定位、Component Contract |
| 13 | `13-cad-anchor-calibration.png` | CAD 锚点人工校准、热点调整、审计记录 |
| 14 | `14-cad-asset-detail.png` | CAD/GLB 模型资产、许可证、SHA、sidecar |
| 15 | `15-work-order-list.png` | 作业票列表、状态、风险等级、筛选 |
| 16 | `16-work-order-safety-execution.png` | 作业票执行、Safety Gate 阻断、状态机 |
| 17 | `17-safety-confirmation-modal.png` | 安全确认弹窗、现场证据、审计日志 |
| 18 | `18-case-draft-generation.png` | 从当前任务生成结构化案例草稿 |
| 19 | `19-case-review-board.png` | 案例审核看板、待审/通过/驳回 |
| 20 | `20-knowledge-write-result-rollback.png` | 知识写入流水线、图谱/索引更新、回滚 |
| 21 | `21-evaluation-overview.png` | 创新指标与四组对比评测 |
| 22 | `22-failure-analysis.png` | 失败样例、误差分析、修复策略 |
| 23 | `23-resource-verification.png` | 手册、图片、CAD、论文、许可证验证 |
| 24 | `24-system-model-routing.png` | 系统管理、模型路由、fallback、索引任务 |
| 25 | `25-field-tablet-execution.png` | 平板现场执行端，强调安全阻断和下一步 SOP |
| 26 | `26-mobile-quick-review.png` | 手机快速复核端，主管/审核人使用 |
| 27 | `27-report-export.png` | 测试报告、评测证明、答辩材料导出 |

## 复刻优先级

P0 页面：

- `01-overview-task-queue.png`
- `02-task-new-empty.png`
- `03-task-generating-agent-progress.png`
- `04-task-result.png`
- `12-cad-structure-main.png`
- `16-work-order-safety-execution.png`
- `18-case-draft-generation.png`
- `21-evaluation-overview.png`

P1 页面：

- `05-vision-ocr-detail.png`
- `07-claim-card-review-detail.png`
- `08-evidence-graph.png`
- `11-insufficient-conflict-review.png`
- `13-cad-anchor-calibration.png`
- `19-case-review-board.png`
- `20-knowledge-write-result-rollback.png`
- `23-resource-verification.png`

P2 页面：

- `06-claim-card-list.png`
- `09-manual-citation-detail.png`
- `10-case-library-detail.png`
- `14-cad-asset-detail.png`
- `15-work-order-list.png`
- `17-safety-confirmation-modal.png`
- `22-failure-analysis.png`
- `24-system-model-routing.png`
- `25-field-tablet-execution.png`
- `26-mobile-quick-review.png`
- `27-report-export.png`

## 复刻注意事项

- 生成图中的小字可能存在变形，不能直接当最终文本；前端实现时必须用真实 HTML 文本。
- 图像用于确定布局、信息层级、状态颜色和组件组合，不用于复制生成图里的错误字形。
- Safety Gate 的红色 BLOCKED 状态必须是页面视觉中心之一，但不能让所有页面都变成红色告警页。
- CAD 页面必须持续显示绑定等级和可信边界：部件级、语义热点、锚点级、需人工校准。
- 模型路由、资源验证、索引重建等管理工具应在信息架构中存在，但不应压过检修主线。

## 自检结论

V2 已从上一版“少量模块概念图”扩展为 28 张完整工作台页面/状态图，覆盖了真实产品使用所需的主要路径。整体风格统一，工业 SaaS 感明显，适合后续作为前端重构视觉基准。

仍需人工把关的地方：

- 局部小字由生成模型产生变形，复刻时替换为真实文案。
- 部分复杂表格只作为密度和布局参考，字段应以当前系统 API 为准。
- CAD 模型图仍是视觉稿，真实前端应继续使用已授权 GLB/CAD 与 sidecar 数据。
