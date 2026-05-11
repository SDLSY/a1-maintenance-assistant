# 授权与引用说明

本说明用于正式提交、开源或答辩时解释系统中的公开资料、依赖和密钥处理方式。它不是法律意见；正式发布前仍应由团队按学校和赛事要求确认授权边界。

## 总原则

- 提交包不包含真实密钥、`.env.local`、SQLite 运行数据库、上传图片、虚拟环境、缓存和原始 PDF。
- 公开厂商 PDF 只用于本地参赛研究、检索索引和引用追踪。
- 图片评测集使用 Wikimedia Commons 的公开候选图，提交包只包含压缩后的评测副本，并保留来源页、许可和本地尺寸信息。
- 系统回答展示来源 URL、页码、许可说明和版本信息，便于答辩现场追溯。
- 未确认再分发授权的原始 PDF 不随作品包发布。
- `.env.example` 只保留变量名和空值，不含真实 key。

## 公开资料来源

来源清单维护在：

```text
data/sources/public_manual_sources.json
```

当前 active 来源 9 个，覆盖电机、离心泵和轴承。

| 设备 | 发布方 | 资料 | 处理方式 |
|---|---|---|---|
| 电机 | ABB | Low Voltage Standard Motors Manual | 本地索引；提交包仅保留 URL/metadata |
| 电机 | WEG | Manual of Electric Motors | 本地索引；提交包仅保留 URL/metadata |
| 电机 | WEG | Low and High Voltage Electric Motors IOM | 本地索引；提交包仅保留 URL/metadata |
| 泵 | Grundfos | CR/CRI/CRN Installation and Operating Instructions | 本地索引；提交包仅保留 URL/metadata |
| 泵 | Grundfos | CR/CRI/CRN Service Instructions | 本地索引；提交包仅保留 URL/metadata |
| 泵 | Grundfos | CR/CRN Air-Cooled Top Supplement | 本地索引；提交包仅保留 URL/metadata |
| 轴承 | SKF | SKF Bearing Maintenance Handbook | 本地索引；提交包仅保留 URL/metadata |
| 轴承 | SKF | Bearing Damage and Failure Analysis | 本地索引；提交包仅保留 URL/metadata |
| 轴承 | SKF | Rolling Bearing Failures Evaluation Guide | 本地索引；提交包仅保留 URL/metadata |

所有来源在 manifest 中标记为：

```text
publicly accessible manufacturer documentation; redistribution not assumed
```

这表示资料可公开访问，但不默认具备再次分发授权。因此提交包排除 `data/raw/manuals/public/*.pdf`。

## 本地生成与团队自建数据

| 数据 | 位置 | 说明 |
|---|---|---|
| 团队自建案例 | `maintenance_cases` / `data/review/mechanical_cases_review.csv` | 当前 125 条，已完成机械审核 |
| 团队自建评测题 | `eval_questions` / `data/review/eval_questions_review.csv` | 当前 104 条，已完成机械审核 |
| 图片评测候选集 | `data/image_eval/images` / `data/image_eval/commons_image_sources.json` | 当前 30 张，覆盖电机、泵、轴承，均保留 Commons 来源和许可 |
| 知识图谱 | SQLite `kg_nodes`, `kg_edges` | 根据设备、部件、故障、风险、案例构建 |
| 人工修正 | SQLite `feedback` | 用户标注模型输出后的修正记录 |
| 提交包 manifest | `SUBMISSION_MANIFEST.md` | 打包脚本自动生成 |

团队自建案例和评测题已经由机械专业角色按 CSV 审核到 `approved` 门槛。系统仍通过 `review_status`、`review_progress.py` 和 `audit_readiness.py` 显式标记审核状态，避免把未审核数据伪装成专家结论。

## 第三方依赖

项目依赖记录在：

```text
requirements.txt
frontend/vendor/
```

主要依赖：

- FastAPI：后端 API 服务。
- Uvicorn：ASGI 服务运行。
- pypdf：PDF 文档解析。
- Vue 3：前端工作台。
- lucide：前端图标。

前端 vendor 文件用于答辩现场离线稳定运行，不依赖 CDN。正式开源时建议补充每个前端 vendor 文件的原始版本号和许可证链接。

## 模型服务与密钥

当前模型路由：

| 角色 | Provider | Model |
|---|---|---|
| 文本、视觉、合规、知识沉淀 | Codex/SpatialAI | `gpt-5.5` |
| embedding | OpenRouter | `qwen/qwen3-embedding-8b` |

密钥处理：

- 真实 key 仅写入本机 `.env.local`。
- `.env.local` 已在 `.gitignore` 中排除。
- `/api/providers`、`/api/agent-routing` 和 `check_deploy.py` 只输出 `key_present=true/false`，不输出真实 key。
- 提交包测试会扫描并排除包含真实密钥风险的文件。

## 提交包排除策略

打包脚本：

```powershell
.\.venv\Scripts\python.exe .\scripts\build_submission_package.py
```

排除内容：

- `.env`
- `.env.local`
- `data/*.db`
- `data/raw/manuals/public/*.pdf`
- `data/uploads/`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `dist/`
- `node_modules/`
- `*.zip`

保留内容：

- 源码。
- 前端静态资源。
- 测试。
- 文档。
- `.env.example`。
- 公开资料 manifest。
- PDF sidecar metadata。
- 机械审核 CSV。
- Wikimedia Commons 图片评测候选集及来源 JSON。
- readiness audit 和审核进度报告。

## 答辩引用建议

答辩中展示公开资料时建议：

- 展示系统内 citation 的来源 URL、页码和标题。
- 不在作品包中直接分发 PDF。
- 如需现场打开 PDF，使用来源 URL 或目标机本地下载副本。
- 对数据来源说明“公开可访问，不默认具备再分发授权，系统仅用于本地参赛研究和引用追溯”。

## 当前结论

当前提交包的授权风险控制策略已经落地：不含密钥、不含运行数据库、不含原始 PDF，不将未审核团队数据伪装成专家数据。正式提交前仍需确认学校/赛事对公开厂商资料展示方式的要求，并完成机械专业审核签核。
