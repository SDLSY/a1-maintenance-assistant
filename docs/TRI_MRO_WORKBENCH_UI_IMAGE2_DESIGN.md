# Tri-MRO 工作台最终版 UI 套图设计

## 设计目标

这套图用于指导 Tri-MRO 工作台重构，不是宣传页，也不是功能 demo。设计对象是一个真实可使用的工业检修作业控制平台，核心链路为：

现场任务 → 多模态输入 → Claim Card → 证据链 → CAD 结构定位 → SOP 作业票 → Safety Gate → 知识写入 → 评测证明 → 系统资源管理。

## 产品框架

一级导航按“检修任务生命周期”组织：

1. 总览与任务队列
2. 检修任务台
3. Claim Card 详情
4. 证据链图谱
5. CAD 结构工位
6. 作业票与安全
7. 知识沉淀
8. 评测与资源
9. 系统与资源管理
10. 现场平板端

每个页面都共享：

- 左侧主导航
- 顶部全局任务条
- 当前设备、型号、component_key
- Evidence Budget 分数
- Safety Gate 状态
- 当前任务阶段

## 全局风格提示词

```text
Create a production-grade Chinese industrial B2B SaaS workbench UI for Tri-MRO, a trustworthy equipment maintenance operation control platform.

The product is not a chatbot and not a pure CAD viewer. It turns one maintenance task into a controlled workflow:
现场输入 → OCR/VLM → Claim Card → Evidence Chain → CAD/Component Grounding → SOP Work Order → Safety Gate → Knowledge Write Pipeline → Evaluation Proof.

Global shell:
- left vertical sidebar navigation
- top global task strip
- current task ID, equipment, model, component_key, evidence score, Safety Gate status
- dense but readable enterprise dashboard
- light gray background, white panels, subtle borders, soft shadows
- deep teal and steel blue primary colors
- red only for BLOCKED / danger
- amber for NEED_REVIEW
- green for READY / verified
- Chinese UI labels
- industrial command console, not consumer app
```

## 约束提示词

```text
Negative constraints:
- Do not design a chatbot-first interface.
- Do not use robot mascots.
- Do not use purple-blue AI startup gradients.
- Do not create a dark cyberpunk dashboard.
- Do not use decorative abstract blobs.
- Do not overclaim CAD face-level precision.
- Do not imply photo-to-CAD can be used for safety approval.
- Do not make Safety Gate a simple reminder; it must look like a blocking control mechanism.
- Do not show API keys or secrets.
- Do not let model provider/debug tools dominate normal workflow pages.
- Do not make unreviewed cases look already written into the knowledge base.
- Use Chinese product labels, but accept that image generation may distort tiny text; final implementation must use real HTML text.
```

## 最终套图

输出目录：

`materials/workbench_design_suite`

| 编号 | 页面 | 文件 |
|---|---|---|
| 01 | 总览与任务队列 | `01-overview-task-queue.png` |
| 02 | 检修任务台 | `02-maintenance-task-console.png` |
| 03 | Claim Card 详情 | `03-claim-card-detail.png` |
| 04 | 证据链图谱 | `04-evidence-graph.png` |
| 05 | CAD 结构工位 | `05-cad-structure-workbench.png` |
| 06 | 作业票与安全 | `06-work-order-safety-gate.png` |
| 07 | 知识沉淀 | `07-knowledge-write-pipeline.png` |
| 08 | 评测与资源 | `08-evaluation-resources.png` |
| 09 | 系统与资源管理 | `09-system-resource-management.png` |
| 10 | 现场平板端 | `10-field-tablet.png` |
| 总览 | 套图接触表 | `workbench-design-suite-contact-sheet.png` |

## 自检结论

- 整体风格统一，均采用工业 SaaS 工作台壳层。
- 页面覆盖完整产品链路，不再是单页 demo。
- 关键产品对象均出现：Claim Card、Evidence Budget、Evidence Chain、Component Contract、CAD 工位、SOP、Safety Gate、Knowledge Write Pipeline、Evaluation Metrics。
- 第 10 张现场平板端、第 06 张作业票与安全、第 05 张 CAD 结构工位最适合作为前端重构参考。
- 小字和部分表格内容存在生成模型常见变形，不能直接作为最终 UI 文案；前端复刻时必须用真实 HTML 文本。
