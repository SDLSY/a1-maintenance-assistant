# 测试报告

报告日期：2026-05-10

## 测试对象

系统名称：A1 多模态设备检修知识检索与作业辅助系统

测试范围：

- PC Web 工作台
- FastAPI 后端接口
- SQLite 数据库与轻量索引
- 公开手册入库与来源追溯
- 文本/图片/型号混合检索
- SOP 生成与合规校验
- 案例上传、审核、知识图谱更新
- 人工修正记录
- 评测面板
- 模型路由与提交包安全

## 测试环境

| 项目 | 当前环境 |
|---|---|
| 操作系统 | Windows 11 |
| CPU 架构 | AMD64 |
| Python | 3.12.7 |
| 数据库 | SQLite 3.45.3 |
| 后端 | FastAPI + Uvicorn |
| 前端 | Vue 3 静态工作台，本地 vendor 依赖 |
| 默认文本/视觉模型 | Codex/SpatialAI `gpt-5.5` |
| 默认 embedding | OpenRouter `qwen/qwen3-embedding-8b` |
| 本地服务 | `http://127.0.0.1:8051` |

LoongArch + 银河麒麟仍需实机验证；当前报告只代表 Windows/AMD64 开发环境。

## 自动化测试

命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

结果：

```text
12 passed, 40 warnings
```

覆盖项：

- `/api/health` 健康检查。
- `/favicon.ico` 不再 404，浏览器 console 不出现 favicon 资源错误。
- 问诊接口返回 SOP、引用、合规项、Agent 轨迹和模型复核信息。
- 案例审核后写入知识图谱。
- 人工修正记录可写入、读取，并在相似问诊中返回提示。
- 供应商/Agent 路由接口不泄露 key。
- 公开来源清单覆盖电机、泵、轴承，且来源 URL 和许可说明完整。
- 机械审核包导出字段完整，测试不污染真实 `data/review`。
- 索引重建和快速评测接口可运行。
- 提交包排除 `.env.local`、数据库、原始 PDF、虚拟环境和缓存。
- readiness audit 能识别真实证据和外部阻塞项。
- 机械审核进度脚本能统计 approved、needs_revision、rejected、unreviewed。

## 部署兼容性检查

命令：

```powershell
.\.venv\Scripts\python.exe .\scripts\check_deploy.py
```

当前结果摘要：

```json
{
  "python": "3.12.7",
  "platform": "Windows-11-10.0.26200-SP0",
  "machine": "AMD64",
  "loongarch_like": false,
  "sqlite": "3.45.3",
  "modules": {
    "fastapi": true,
    "uvicorn": true,
    "pypdf": true
  }
}
```

结论：当前开发机依赖检查通过，但不是 LoongArch。最终提交前必须在 LoongArch + 银河麒麟上重新执行该脚本。

## 数据与索引测试

当前数据状态：

| 指标 | 数量 |
|---|---:|
| 文档数 | 13 |
| 手册 chunk | 1108 |
| 带来源 URL 的 chunk | 1092 |
| OpenRouter embedding 向量 | 1233 |
| 公开来源 | 9 |
| 团队自建案例 | 125 |
| 团队自建评测题 | 104 |

公开来源覆盖：

- 电机：ABB、WEG 等公开手册。
- 泵：Grundfos 等公开手册。
- 轴承：SKF 维护、失效分析等公开手册。

验证点：

- 手册入库保留来源 URL、页码、许可说明和版本信息。
- 检索返回引用证据，不只返回模型生成内容。
- 提交包不再分发原始 PDF，只保留来源清单和 sidecar metadata。

## 模型路由测试

当前角色路由：

| 角色 | Provider | Model |
|---|---|---|
| 文本诊断/SOP | codex | gpt-5.5 |
| 图片描述 | codex | gpt-5.5 |
| 向量检索 | openrouter | qwen/qwen3-embedding-8b |
| 合规复核 | codex | gpt-5.5 |
| 知识沉淀 | codex | gpt-5.5 |

验证点：

- `/api/providers` 和 `/api/agent-routing` 只返回 key 是否存在，不返回真实 key。
- OpenRouter embedding 已重建为 4096 维远程向量，当前数据库中 embedding 模型为 `qwen/qwen3-embedding-8b`。
- Claude/SpatialAI 和 OpenCode/Zen 保留为备选供应商，但不作为默认运行时路由。

## 功能测试

| 功能 | 状态 | 证据 |
|---|---|---|
| 文本故障问诊 | 通过 | 问诊接口返回诊断、SOP、引用、合规项 |
| 图片故障输入 | 通过 | 图片上传接口返回 caption，参与问诊检索 |
| 设备型号过滤 | 通过 | 检索层按设备类型和型号过滤候选 |
| 手册引用 | 通过 | citation 包含来源、页码、URL、许可 |
| 标准作业指引 | 通过 | SOP 包含安全确认、拆检步骤、验收标准 |
| 合规校验 | 通过 | LOTO、PPE、泄压/降温、防误启动等规则检查 |
| 案例上传审核 | 通过 | 待审核案例通过后写入案例库和图谱 |
| 人工修正 | 通过 | `/api/feedback` 支持写入、读取和相似提示 |
| 知识图谱 | 通过 | 前端可视化设备、部件、故障、案例关系 |
| 评测面板 | 通过 | 支持快速评测、完整评测、审核题优先 |
| 提交包安全 | 通过 | ZIP 禁入文件 0 个 |

## 浏览器测试

工具：Playwright CLI

已验证页面：

- 首页问诊检修
- 评测面板
- 资源与模型
- 知识图谱
- 案例审核

结果：

```text
console errors: 0
console warnings: 0
```

## 评测结果

当前快速评测可运行，且 `audit_readiness.py` 能读取真实数据库状态。由于机械审核尚未回写，评测基准仍标记为未审核兜底：

| 指标 | 当前状态 |
|---|---|
| Recall@5 | 快速评测通过 |
| 引用覆盖率 | 快速评测通过 |
| SOP 完整度 | 快速评测通过 |
| 安全漏检 | 快速评测通过 |
| 审核基准 | `unreviewed_fallback` |

正式报告需要在机械专业队友审核 CSV 并回写后重新运行完整评测。

## 机械审核测试

当前审核 CSV 状态：

| 数据集 | Total | Approved | Unreviewed |
|---|---:|---:|---:|
| 案例 | 125 | 0 | 125 |
| 评测题 | 104 | 0 | 104 |

命令：

```powershell
.\.venv\Scripts\python.exe .\scripts\review_progress.py
```

当前结果：

```text
ready_for_import=false
ready_for_goal=false
```

需要机械专业队友审核并回写至少 100 条 approved 案例和 100 条 approved 评测题。

## 提交包测试

命令：

```powershell
.\.venv\Scripts\python.exe .\scripts\build_submission_package.py --timestamp 20260510-readiness-final
.\.venv\Scripts\python.exe .\scripts\audit_readiness.py --submission-archive .\dist\a1-maintenance-assistant-submission-20260510-readiness-final.zip
```

当前结果：

```text
entries=66
forbidden=0
ready=false
```

禁入文件包括：

- `.env`
- `.env.local`
- SQLite 运行数据库
- 原始 PDF
- 虚拟环境
- 缓存目录
- zip 套 zip

## 风险与未完成项

| 风险 | 当前处理 |
|---|---|
| 机械专业审核未完成 | 已导出 CSV、提供审核指南和进度脚本 |
| LoongArch 实机未验证 | 已提供部署文档、检查脚本和 readiness audit 阻塞提示 |
| 公开 PDF 再分发授权不确定 | 提交包不包含 PDF，只保留来源 URL 和 metadata |
| 评测集仍未签核 | 审计报告保持 `ready=false`，避免误判完成 |

## 结论

开发环境下，系统主链路、自动化测试、浏览器检查、模型路由、索引和提交包安全均已通过。当前不能视为正式参赛完成，原因是缺少机械专业审核签核和 LoongArch + 银河麒麟实机验证。
