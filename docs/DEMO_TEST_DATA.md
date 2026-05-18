# A1 演示测试数据清单

这份清单用于现场演示，不需要临时想输入内容。建议演示前打开 `http://127.0.0.1:8051`，按下面顺序跑。机器可读版本在 `data/demo/demo_scenarios.json`。

## 演示顺序

1. 电机轴承温升文本问诊
2. 离心泵机械密封泄漏图文检索
3. 轴承外圈剥落图片定位
4. 官方发动机手册样例问答
5. 从当前任务生成案例
6. 评测与资源证明

## 1. 电机轴承温升文本问诊

页面：检修任务台

输入：

```text
设备类型：motor / 电机
设备型号：Y2-160M
检修等级：二级检修
故障描述：电机运行 30 分钟后端盖温度升高，伴随低频振动和轴承异响。请给出故障判断、拆检前安全确认、SOP 和验收标准。
```

预期展示：

- 顶部 workflow 出现：现场感知、检索、CAD 部件定位、SOP、安全闸门。
- 业务部件应落到 `motor.bearing`。
- CAD/3D 模型节点通常落到 `front_bearing_end` 或 `end_cover`。
- 重点讲：证据可追溯、SOP 可执行、安全闸门不是装饰。

## 2. 离心泵机械密封泄漏图文检索

页面：检修任务台

输入：

```text
设备类型：pump / 离心泵
设备型号：mini-vacuum-pump
检修等级：三级检修
故障描述：离心泵机械密封连续滴漏，密封端有泄漏痕迹，现场需要隔离介质、泄压后拆检。请结合图片给出密封组件检查步骤。
```

上传图片：

```text
data/image_eval/images/pump_mechanical_seal_parts_01.jpg
```

预期展示：

- 图片描述、缺陷标签、OCR/VLM 结果参与检索。
- 业务部件应落到 `pump.mechanical_seal`。
- CAD/3D 模型节点通常落到 `pump_seal_zone` 或 `pump_shaft`。
- 安全项应出现隔离、泄压、PPE、防滑、试压/复测。

讲解话术：

> 这不是让大模型看图瞎猜，而是把图片转换成结构化现场证据，再进入手册、案例和图谱检索，最后落到 CAD 部件和 SOP 步骤。

## 3. 轴承外圈剥落图片定位

页面：检修任务台，然后切到 CAD 结构工位

输入：

```text
设备类型：bearing / 轴承
设备型号：6201-2RS
检修等级：二级检修
故障描述：结合上传图片判断轴承滚道是否存在磨损、剥落或压痕，并生成拆检步骤。要求定位到 3D 标准轴承模型中的相关部件。
```

上传图片：

```text
data/image_eval/images/bearing_damage_nara_01.jpg
```

预期展示：

- 业务部件应落到 `bearing.outer_ring` 或 `bearing.rolling_elements`。
- CAD/3D 模型节点应落到 `outer_ring` 或 `rolling_elements`。
- SOP 应包含停机/断电、清洁度控制、禁止硬敲滚道、复测振动/温升。

## 4. 官方发动机手册样例问答

页面：检修任务台

输入：

```text
设备类型：engine / 发动机
设备型号：motorcycle-engine-hd
检修等级：二级检修
故障描述：发动机冷车起动困难，火花塞有积碳，怀疑间隙异常。请依据维修手册给出火花塞检查、压缩压力复核和复装注意事项。
```

预期展示：

- 引用中应能看到官方样例手册相关证据。
- 业务部件应落到 `engine.spark_plug`。
- CAD/3D 模型节点应落到 `spark_plug`。
- 重点讲：系统能适配官方给定资料，不只服务我们自选的电机/泵/轴承。

## 5. 从当前任务生成案例

推荐先完成第 2 条泵机械密封场景。

操作：

1. 点击顶部任务条中的“从当前任务生成案例”。
2. 页面跳到“案例沉淀”。
3. 检查表单是否自动带入标题、设备型号、故障现象、原因、处置措施和风险等级。
4. 点击提交待审核。
5. 在待审核列表点击审核入库。
6. 切到证据链图谱，说明案例审核后进入知识闭环。

预期展示：

- 标题包含“当前任务沉淀”。
- 故障现象包含“机械密封连续滴漏”。
- 处置措施包含隔离、泄压、密封组件检查/更换。

## 6. 评测与资源证明

页面：评测证明、资源与模型

演示点：

- 评测证明：展示 Recall@5、引用覆盖率、SOP 完整度、安全漏检率、视觉 Top-5。
- 资源与模型：展示图片评测 gate、资源验证、授权 3D 资产、CAD/GLB 来源。
- 四组对比：无 RAG、文本 RAG、多模态 RAG、本系统。

讲解话术：

> 我们的竞争点不是单纯 OCR+VLM，而是把现场输入、证据链、CAD 部件定位、SOP、安全闸门、案例审核和评测证明整合成一条可复核的检修流程。

## 快速图片池

| 场景 | 图片路径 | 用途 |
|---|---|---|
| 电机轴承 | `data/image_eval/images/motor_bearing_grease_seal_01.jpg` | 端盖、轴承、润滑密封 |
| 电机过热 | `data/image_eval/images/motor_overheat_burnt_motor_01.jpg` | 过热、绝缘、通风风险 |
| 泵机械密封 | `data/image_eval/images/pump_mechanical_seal_parts_01.jpg` | 机械密封部件定位 |
| 泵泄漏污迹 | `data/image_eval/images/pump_raw_water_failure_01.jpg` | 密封失效、泄漏污迹 |
| 轴承滚道损伤 | `data/image_eval/images/bearing_damage_nara_01.jpg` | 外圈/滚道损伤 |
| 轴承失效 | `data/image_eval/images/bearing_failed_photo_01.jpg` | 轴承失效实物照片 |

## 现场兜底输入

如果图片上传或云模型较慢，使用纯文本也能演示主链路：

```text
设备类型：pump
设备型号：mini-vacuum-pump
检修等级：三级检修
故障描述：离心泵密封端连续滴漏，泵体底座有积液，现场需要先隔离介质、泄压排液，再检查机械密封、O 形圈和轴套磨损。
```

如果想展示“可信边界”，使用：

```text
设备类型：pump
设备型号：UNKNOWN-XJ999
检修等级：一级检修
故障描述：现场发现未知型号泵组有异常气味和轻微渗漏，但没有铭牌、运行参数和清晰照片。请判断是否可以直接拆检。
```

讲解重点：证据不足时系统应提示补充信息、人工复核和安全确认，而不是包装成确定结论。

## 演示前检查

```powershell
cd D:\30726\Desktop\竞赛目录\a1-maintenance-assistant
.\.venv\Scripts\python.exe -m pytest tests/test_api.py::test_query_returns_integrated_workflow_state tests/test_graph_frontend_readability.py::test_frontend_exposes_integrated_maintenance_session -q
```

预期：

```text
2 passed
```

## Tri-MRO 最终版测试对象

机器可读操作矩阵：`data/demo/tri_mro_operation_matrix.json`。

每条正式演示样例都必须确认以下对象可见：

- `检修判断卡`：包含故障判断、置信等级、证据链、结构链、作业链和复核策略。
- `证据预算`：展示手册证据、案例证据、图谱路径和视觉证据四类分数；证据不足时不得输出确定结论。
- `部件约束`：统一 OCR/VLM、RAG、图谱、CAD、SOP、案例中的部件标识。
- `安全闸门`：高风险步骤未满足断电、泄压、温度、PPE、工具等条件时必须阻断或转人工复核。
- `FMEA 风险链`：展示故障模式、可能原因、影响、RPN 和推荐动作。
- `知识写入流水线`：案例审核后的知识写入流水线，展示影响部件、图谱更新、索引更新、回滚号和回归评测。
- `创新指标`：展示关键结论可追溯率、三链对齐覆盖率、CAD 部件定位首位命中/前三命中、高风险步骤阻断率、拒答合理率、知识更新后召回提升率和知识污染拦截率。

## 全操作测试顺序

1. `检修任务台`：依次跑电机、泵、轴承、发动机 4 个黄金样例，检查检修判断卡、证据预算、FMEA 风险链、SOP 和安全闸门。
2. `CAD 结构工位`：从生成结果进入 CAD，确认 3D canvas 非空；切换电机、泵、轴承、发动机模型；检查部件约束、绑定等级和人工校准说明。
3. `案例沉淀`：从当前任务生成案例，确认可返回诊断结果；提交待审核案例后审核入库，检查知识写入流水线。
4. `证据链图谱`：确认当前任务证据链可见，节点不堆叠成不可读全量图。
5. `评测证明`：确认四组对比和创新指标可见。
6. `资源与模型`：确认资源验证、授权 CAD/GLB、sidecar、转换报告和图片资产状态可访问。
7. `反例链路`：使用未知型号、证据不足、直接拆卸、文本图片冲突样例，确认系统会拒答、阻断或转人工复核。

## 推荐测试命令

```powershell
cd D:\30726\Desktop\竞赛目录\a1-maintenance-assistant

# 后端/前端静态与最终版对象
.\.venv\Scripts\python.exe -m pytest tests/test_tri_mro_final.py tests/test_system_smoke.py -q
node --check frontend\app.js

# 启动服务后执行 API + 浏览器烟测
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8051
.\.venv\Scripts\python.exe scripts\system_smoke.py --base-url http://127.0.0.1:8051
```

测试报告输出：

- `test-results/system-smoke-report.json`
- `test-results/system-smoke-report.md`
- `test-results/system-smoke-screenshots/`
