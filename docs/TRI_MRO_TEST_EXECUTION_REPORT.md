# Tri-MRO 完整测试执行报告

生成时间：2026-05-15

## 结论

本轮按 `docs/TRI_MRO_TEST_PLAN.md` 和 `data/demo/tri_mro_test_cases.json` 执行完整测试。结论如下：

- 项目内 pytest：`105 passed`
- 前端语法检查：`node --check frontend/app.js` 通过
- 完整测试计划执行器：`68` 项测试登记，`54` 项已通过，`0` 项自动化失败
- 浏览器系统 smoke：通过，blocker 为 `0`
- API smoke：通过
- 浏览器 console error：`0`

重要边界：

- `T43` 案例驳回、`T46` 真正回滚、`T120` 多角色审核权限当前没有完整后端能力，已标记为 `not_implemented`，不能包装成通过。
- `T45` 知识污染拦截、`T53` CAD 热点人工校准、`T63` 引用真实性、`T112` 无关图片、`T113` 重复提交需要人工验收或机械专业判断。
- `T130-T133` LoongArch + 银河麒麟需要目标环境，当前标记为 `environment_blocked`。

## 执行命令

```powershell
.\.venv\Scripts\python.exe scripts\execute_tri_mro_test_plan.py
.\.venv\Scripts\python.exe -m pytest -q
node --check frontend\app.js
.\.venv\Scripts\python.exe scripts\system_smoke.py --base-url http://127.0.0.1:8051
```

## 自动化结果摘要

| 项目 | 结果 |
|---|---:|
| 测试用例总数 | 68 |
| 已通过 | 54 |
| 自动化通过 | 53 |
| 自动化失败 | 0 |
| 浏览器 smoke 覆盖项 | 2 |
| 人工待验收 | 5 |
| 环境阻塞 | 4 |
| 当前未实现 | 3 |

## 已通过的核心能力

| 能力 | 验证结果 |
|---|---|
| 系统启动和健康检查 | 通过 |
| 检修任务台文本问诊 | 通过 |
| 图片上传和视觉分析 | 通过 |
| 手册/案例/图谱检索 | 通过 |
| Claim Card 字段完整性 | 通过 |
| Evidence Budget 阈值一致性 | 通过 |
| 不支持设备/空任务降级 | 通过 |
| 文本图片冲突人工复核 | 通过 |
| Component Contract 一致性 | 通过 |
| CAD/3D 四类设备模型 | 通过 |
| CAD 绑定等级和可信边界 | 通过 |
| SOP 作业票 | 通过 |
| Safety Gate 直接拆卸阻断 | 通过 |
| FMEA Risk Chain | 通过 |
| Knowledge Write Pipeline 审核通过入库记录 | 通过 |
| Innovation Metrics | 通过 |
| 四组对比评测接口 | 通过 |
| 资源验证 | 通过 |
| fallback 本地模式 | 通过 |

## 已修复的问题

| 问题 | 修复 |
|---|---|
| 不支持设备或空任务可能获得高证据分 | Claim Card 层增加 unsupported/empty task 降级，证据分封顶并触发复核或拒答 |
| 文本和图片冲突未显式标记 | Claim Card 增加 `conflict_detected`，冲突时 Evidence Budget 降级为 `confirm` |
| 完整测试计划没有结构化执行入口 | 新增 `data/demo/tri_mro_test_cases.json` 和 `scripts/execute_tri_mro_test_plan.py` |
| 全量测试计划没有正式文档 | 新增 `docs/TRI_MRO_TEST_PLAN.md` |

## 待人工验收项

| ID | 项目 | 原因 |
|---|---|---|
| T45 | 知识污染拦截 | 需要机械专业或审核人判断错误案例是否应驳回 |
| T53 | CAD 热点人工校准 | 需要 UI 手工拖动/保存/刷新验证 |
| T63 | 引用真实性 | 需要人工检查引用是否真实支撑结论 |
| T112 | 无关图片 | 需要真实无关图片和人工判断 |
| T113 | 重复提交 | 需要人工结合业务预期判断去重策略 |

## 当前未实现项

| ID | 项目 | 说明 |
|---|---|---|
| T43 | 审核驳回案例 | 当前有候选 CAD 驳回，但普通检修案例缺少 reject case API |
| T46 | 知识回滚 | 当前有 `rollback_id` 记录，但没有执行回滚接口 |
| T120 | 角色权限 | 当前没有登录/角色权限系统，无法验证普通用户不可审核 |

## 环境阻塞项

| ID | 项目 | 阻塞 |
|---|---|---|
| T130 | LoongArch 基础环境验证 | 缺少 LoongArch + 银河麒麟实机/官方云环境 |
| T131 | LoongArch 服务启动 | 缺少目标环境 |
| T132 | LoongArch 最小主链路 | 缺少目标环境 |
| T133 | LoongArch fallback 模式 | 缺少目标环境 |

## 产物位置

- 测试计划：`docs/TRI_MRO_TEST_PLAN.md`
- 测试用例：`data/demo/tri_mro_test_cases.json`
- 完整测试执行 JSON：`test-results/tri-mro-full-test-execution.json`
- 完整测试执行 Markdown：`test-results/tri-mro-full-test-execution.md`
- 浏览器 smoke JSON：`test-results/system-smoke-report.json`
- 浏览器 smoke Markdown：`test-results/system-smoke-report.md`

## 下一步建议

1. 优先实现 `T43` 案例驳回和 `T46` 回滚接口，补齐知识治理闭环。
2. 若要强调工程可信度，补一个轻量角色模型，覆盖 `T120`。
3. 安排机械专业队友按本报告中的人工验收项逐条签字或给出审核代号。
4. 获得 LoongArch + 银河麒麟环境后，按 `T130-T133` 最小链路补截图、日志和录屏。
