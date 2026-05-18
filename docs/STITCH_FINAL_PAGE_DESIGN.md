# Tri-MRO Stitch 最终版页面设计记录

本文记录本轮使用 Stitch 生成的“方案二：事故阻断叙事版”全套页面设计稿，并说明这些设计如何落地到当前项目。它可以作为后续 UI 重构、答辩视觉验收和宣传页迭代的交接文档。

## Stitch 项目

- Project：`Tri-MRO Final Incident-Blocked Full Pages`
- Project ID：`4517672510672491425`
- Design system asset：`assets/7360c53f60d240878c586dddb11f835f`
- Design system name：`Tri-MRO Industrial Design System`

## 设计主线

Tri-MRO 不是聊天机器人，也不是单纯 CAD 查看器。最终 UI 主线固定为：

> 系统没有急着回答“怎么修”，而是先判断“现在能不能修”。

全套页面围绕一次离心泵机械密封泄漏检修任务展开：

```text
现场输入
→ Claim Card 检修判断卡
→ Evidence Budget 证据预算
→ CAD/GLB 结构定位
→ SOP 作业票
→ Safety Gate 阻断或放行
→ Knowledge Write Pipeline 审核入库
→ 证据链与评测证明
```

## Stitch 页面清单

| 页面 | Stitch screen id | 设计定位 |
| --- | --- | --- |
| 宣传主页 | `5eecf7dcea30493f8beaa66c5e19c015` | 事故阻断叙事营销页，首屏用 `BLOCKED` 建立记忆点 |
| 检修任务 | `8d19b79017984b3ca5c7eb26e68aa1d7` | 三栏布局：现场输入、Claim Card、下一步动作和 Safety Gate |
| 结构工位 | `d03cb6f097694f33be4eea7efdfce717` | CAD/GLB 部件定位，强调 Component Contract 和绑定等级 |
| 作业票与安全 | `1251d75ea30c42ec8c4d3c63485c2ea1` | 核心演示页：SOP 时间线 + Safety Gate 状态机阻断 |
| 知识沉淀 | `bea156809a7044d7bf595a671776ed5d` | Knowledge Write Pipeline：审核后才写入案例库、图谱和索引 |
| 证据链 | `888f9d3d9c31400fa0c829a23340119e` | 当前 Claim Card 的线性证据路径，避免全量图谱堆叠 |
| 评测与资源 | `d221f90f3c004fcba1cde1a89829e48e` | 创新指标、四组对比、资源验证和高级工具折叠 |

## 本地实现映射

| Stitch 页面 | 本地实现 |
| --- | --- |
| 宣传主页 | `/marketing`、`/promo`；文件：`frontend/marketing.html`、`frontend/marketing.css`、`frontend/marketing.js` |
| 检修任务 | `/` 默认页，`activeTab === "diagnosis"` |
| 结构工位 | `/` 中 `activeTab === "spatial"` |
| 作业票与安全 | `/` 中 `activeTab === "safety"` |
| 知识沉淀 | `/` 中 `activeTab === "cases"` |
| 证据链 | `/` 中 `activeTab === "graph"` |
| 评测与资源 | `/` 中 `activeTab === "metrics"` 与 `activeTab === "resources"` |

## 视觉约束

- 主色：深青 `#0F766E`，钢蓝 `#286581`。
- 状态色：`BLOCKED #B42318`，`WAITING #B7791F`，`READY #16835D`。
- 背景：冷灰浅色，不使用紫蓝 AI 渐变、机器人、聊天气泡、赛博霓虹或装饰光球。
- CAD 只表达部件级、锚点级、语义热点绑定，不声称面级精确测量。
- photo-to-CAD 只保留为实验链路，不作为安全放行依据。
- 页面叙事必须突出“有证据、能定位、可执行、可阻断、可沉淀”。

## 落地范围

本轮已将方案二设计主线落入当前原生 Vue 工作台：

- 默认演示场景切换为“离心泵机械密封泄漏 + 高风险直接拆卸请求”。
- 新增 `/marketing` 与 `/promo` 事故阻断叙事宣传主页。
- 主导航补入 `作业票与安全` 一级模块。
- 全局增加事故阻断状态条，状态从 `BLOCKED` 到 `READY` 时同步切换安全 chip。
- 新增 Safety Gate 作业票页面：SOP 时间线、安全确认、阻断原因、审计留痕、工具备件、验收标准。
- 结构工位中 Component Contract 的安全门显示为中文工程语义，不暴露后端 key。
- 系统 smoke 覆盖 `/marketing`、检修任务、CAD 工位、作业票与安全、知识沉淀、证据链、评测证明和资源资产。
- 新增最终演示录屏脚本 `scripts/record_final_incident_demo.py`。

## 验证记录

已执行的关键命令：

```text
node --check frontend/app.js
node --check frontend/marketing.js
pytest tests/test_marketing_homepage.py tests/test_system_smoke.py -q
pytest tests/test_tri_mro_final.py -q
pytest tests/test_api.py -vv
pytest tests/test_3d_component_semantics.py tests/test_cad_3d_bridge.py tests/test_runtime_responsiveness.py tests/test_graph_frontend_readability.py tests/test_candidate_cad_frontend.py -q
pytest tests/test_candidate_cad_final_pipeline.py tests/test_part_tree_candidates.py tests/test_photo_to_3d_collected_assets.py -q
python scripts/system_smoke.py --base-url http://127.0.0.1:8051
python scripts/record_final_incident_demo.py
```

生成物：

- 浏览器 smoke 报告：`test-results/system-smoke-report.md`
- 浏览器截图目录：`test-results/system-smoke-screenshots/`
- 最终演示视频：`materials/demo_videos/tri_mro_final_incident_demo.mp4`
- 视频字幕说明：`materials/demo_videos/tri_mro_final_incident_demo_subtitles.txt`
