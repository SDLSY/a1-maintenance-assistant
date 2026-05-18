# A1/Tri-MRO 全操作测试与演示数据整理

生成时间：2026-05-15

## 测试结论

本轮已完成一轮面向演示和答辩的全操作路径测试，覆盖检修任务台、Claim Card、CAD 工位、案例沉淀、证据链图谱、评测证明、资源页、候选 CAD 实验链路和主要 API 合约。

当前结论：

- 项目内自动化测试：`100 passed`
- 浏览器系统 smoke：`passed`
- API 合约检查：`16/16 passed`
- 浏览器操作步骤：`20/20 passed`
- Console errors：`0`
- Smoke blockers：`0`

## 测试命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --check frontend\app.js
.\.venv\Scripts\python.exe scripts\system_smoke.py --base-url http://127.0.0.1:8051
```

说明：已新增 `pytest.ini`，将 pytest 收集范围限定为 `tests/`，避免误收集 `tools/openscad` 中第三方 OpenSCAD/MCAD 自带测试。

## 报告文件

- 机器可读 smoke 报告：`test-results/system-smoke-report.json`
- Markdown smoke 报告：`test-results/system-smoke-report.md`
- 演示测试数据说明：`docs/DEMO_TEST_DATA.md`
- 全操作矩阵：`data/demo/tri_mro_operation_matrix.json`

## 已覆盖模块

| 模块 | 覆盖内容 | 状态 |
|---|---|---|
| 检修任务台 | 文本问诊、四类设备、Claim Card、Evidence Budget、FMEA Risk Chain | 通过 |
| CAD 结构工位 | 首次进入、二次进入、设备切换、剖视平面、复位视角、同步问诊方案 | 通过 |
| Component Contract | CAD 工位展示部件契约、绑定等级、人工校准边界 | 通过 |
| 案例沉淀 | 从当前任务生成案例、返回诊断、Knowledge Write Pipeline 可见 | 通过 |
| 证据链图谱 | 当前任务证据链页面可进入，无空白页和 console error | 通过 |
| 评测证明 | Innovation Metrics、四组对比指标入口可见 | 通过 |
| 资源与模型 | 资源验证、CAD/GLB 预览链接、候选 CAD 文件角色 | 通过 |
| API 合约 | `/api/query`、`/api/3d/models`、`/api/3d/guidance`、`/api/metrics`、`/api/resources/verification`、`/api/knowledge-graph` | 通过 |

## 黄金演示样例

| ID | 场景 | 设备 | 目标部件 | 预期机制 |
|---|---|---|---|---|
| G01 | 电机轴承温升异常 | motor | `motor.bearing` | 证据链 + SOP + 安全闸门 + CAD 定位 |
| G02 | 离心泵机械密封泄漏 | pump | `pump.mechanical_seal` | Claim Card + 阻断拆检 + 知识写入流水线 |
| G03 | 轴承外圈剥落 | bearing | `bearing.outer_ring` / `bearing.rolling_elements` | 图片识别 + 结构链定位 + SOP |
| G04 | 官方发动机火花塞检查 | engine | `engine.spark_plug` | 官方手册引用 + FMEA 风险链 |

## 反例/安全样例

| ID | 场景 | 预期行为 |
|---|---|---|
| A01 | 设备型号和现场证据不足 | Evidence Budget 低于阈值，拒答或只给排查方向 |
| A02 | 用户要求直接拆卸 | Safety Gate 阻断，要求确认断电、泄压、PPE、温度和工具 |
| A03 | 文本与图片冲突 | 标记冲突，要求人工复核，不输出确定结论 |

## 本轮修复点

- 修复浏览器 E2E 中“生成检修方案”等待过短导致 Claim Card/FMEA 假失败的问题。
- 修复候选 CAD 预览接口未允许 `data/cad_candidates` 资源根的问题。
- 修复候选 CAD 无 sidecar/转换报告时仍暴露不可访问预览链接的问题。
- 修复 CAD 切换泵模型时标题断言仍使用旧英文关键字的问题。
- 新增 `pytest.ini`，保证 `pytest -q` 只运行项目测试。

## 当前可演示入口

```text
http://127.0.0.1:8051/?tri_mro_operation_test=1
```

建议演示顺序：

1. 离心泵机械密封泄漏：展示 Claim Card、Evidence Budget、CAD 定位和安全阻断。
2. 进入 CAD 工位：切换泵、轴承、电机、发动机，展示 Component Contract 和绑定等级。
3. 从当前任务生成案例：展示 Knowledge Write Pipeline。
4. 进入评测证明：展示 Innovation Metrics。
5. 用证据不足样例演示拒答或人工复核。
