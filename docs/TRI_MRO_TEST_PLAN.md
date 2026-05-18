# Tri-MRO 项目详细测试计划

生成时间：2026-05-15

## 测试目标

本测试计划用于验证 Tri-MRO 不是普通“多模态问答系统”，而是一个证据治理型检修作业控制系统。测试重点不是页面能打开，而是验证每个检修判断是否满足：

- Claim Card：故障判断结构化。
- Evidence Budget：证据分影响回答、降级、拒答或复核策略。
- Evidence Chain：关键结论有手册、案例、图谱或视觉证据支撑。
- Component Contract：图片、检索、CAD、SOP、案例统一使用 `component_key`。
- Safety Gate：高风险作业未满足安全条件时可以阻断。
- FMEA Risk Chain：故障模式、影响、风险等级和处置建议可解释。
- Knowledge Write Pipeline：案例审核后才写入知识库、图谱和索引。
- Innovation Metrics：指标能解释 Tri-MRO 相比普通 RAG 的价值。

## 测试范围

纳入测试：

- PC Web 检修任务台、CAD 结构工位、证据链图谱、案例沉淀、评测证明、资源与模型。
- 文本、图片、设备型号输入。
- 手册、案例、图谱、视觉标签检索。
- Claim Card、Evidence Budget、Evidence Chain、Structure Chain、Operation Chain。
- SOP 作业票、Safety Gate、FMEA Risk Chain。
- Knowledge Write Pipeline 和创新指标。
- fallback、资源验证和 LoongArch 最小运行计划。

暂不作为主线通过项：

- photo-to-3D / photo-to-CAD：只作为实验链路。
- CAD 面级精确绑定：当前仅验证部件级、锚点级、语义热点和人工校准提示。
- 移动 App：PC Web 已满足赛题可视化界面要求。
- LoongArch 实机：没有实机时只能标记为环境阻塞或风险说明，不能声称通过。

## 优先级

- P0：影响比赛主线，必须通过或明确阻塞。
- P1：强烈建议通过，影响可信度和获奖质量。
- P2：锦上添花，不影响主链路验收。

## 结构化测试数据

可执行测试用例见：

```text
data/demo/tri_mro_test_cases.json
```

测试执行器：

```text
scripts/execute_tri_mro_test_plan.py
```

测试报告输出：

```text
test-results/tri-mro-full-test-execution.json
test-results/tri-mro-full-test-execution.md
```

## 黄金样例

| 编号 | 场景 | 目标部件 | 主要验证点 |
|---|---|---|---|
| G01 | 电机轴承温升异常 | `motor.bearing` | 文本问诊、证据链、SOP、安全检查、CAD 定位 |
| G02 | 离心泵机械密封泄漏 | `pump.mechanical_seal` | 图片/文本融合、泄压闸门、案例沉淀 |
| G03 | 轴承外圈剥落 | `bearing.outer_ring` / `bearing.rolling_elements` | 轴承 CAD、结构链、FMEA |
| G04 | 发动机火花塞检查 | `engine.spark_plug` | 官方手册样例、发动机 SOP |

## 反例样例

| 编号 | 场景 | 预期行为 |
|---|---|---|
| A01 | 证据不足 | 拒答、降级或人工复核 |
| A02 | 用户要求直接拆卸 | Safety Gate 阻断 |
| A03 | 文本和图片冲突 | 冲突检测并人工复核 |
| A04 | 不支持设备类型 | 不高置信回答，不强行匹配 |
| A05 | 云模型失败 | fallback 可用 |
| A06 | 错误案例试图入库 | 需要审核或拦截 |
| A07 | CAD 无精确锚点 | 显示绑定等级和人工校准 |
| A08 | 绕过安全确认 | 后端不能放行高风险步骤 |

## 自动化执行策略

自动化执行器对可程序化验证的测试项直接调用 FastAPI TestClient、文件检查和模型/资源检查。浏览器交互由 `scripts/system_smoke.py` 执行。人工判断项会在报告中标记为 `manual_required`；环境项会标记为 `environment_blocked`；当前未实现的权限/回滚类功能会标记为 `not_implemented`，不包装成通过。

## 退出标准

- P0 自动化用例通过。
- 浏览器 smoke 通过且无 console error。
- G01-G04 至少 3 条完整通过，G02 作为主演示链路必须通过。
- A01-A03 反例通过。
- Safety Gate 高风险拆卸必须阻断。
- 审核前案例不得进入正式检索；审核后必须有知识写入记录。
- CAD 绑定等级清楚，不夸大为面级精确绑定。
- LoongArch 未实机验证时必须在报告中明确标记风险。
