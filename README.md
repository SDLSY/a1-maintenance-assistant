# A1 多模态设备检修知识检索与作业辅助系统

面向中国软件杯 A1 赛题的可运行原型。系统聚焦电机、离心泵、轴承三类设备，覆盖多模态检索、检修手册引用、标准化作业指引、合规校验、案例审核、人工修正闭环、知识图谱更新和评测面板。

## 快速启动

```powershell
cd D:\30726\Desktop\竞赛目录\a1-maintenance-assistant
.\scripts\run_server.ps1
```

## 公网演示部署

当前推荐先使用方案 B：Cloudflare Pages 托管静态前端，Render 托管 FastAPI 后端，Supabase 持久化案例、审核状态和人工修正。SQLite 仍保留为本地检索索引和演示数据缓存。

Supabase 初始化 SQL 见 [docs/SUPABASE_SCHEMA.sql](docs/SUPABASE_SCHEMA.sql)，完整部署步骤见 [docs/DEPLOYMENT_PUBLIC.md](docs/DEPLOYMENT_PUBLIC.md)。

生成 Cloudflare Pages 静态目录：

```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_cloudflare_site.py --api-base-url https://<backend-domain> --output-dir .\dist\cloudflare-site
```

Render 后端启动命令：

```text
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

公网演示阶段的审计命令：

```powershell
.\.venv\Scripts\python.exe .\scripts\audit_readiness.py --deployment-mode public --submission-archive .\dist\a1-maintenance-assistant-submission-20260511-public-deploy.zip
```

真实模型 key、`SUPABASE_SECRET_KEY` 和 `SUPABASE_SERVICE_ROLE_KEY` 只放在后端环境变量中，不放入前端和提交包。

浏览器打开：

```text
http://127.0.0.1:8051
```

## 模型配置

`.env.local` 分成两层：

1. 凭证层：保存 OpenAI、OpenCode/Zen、SpatialAI/Claude 的 base URL 和 key。
2. 角色路由层：决定每类 Agent 用哪个 provider 和哪个 model。

项目已经内置两套可切换配置：

```powershell
# 查看配置
.\.venv\Scripts\python.exe .\scripts\apply_model_profile.py --list

# 现有高效果演示配置
.\.venv\Scripts\python.exe .\scripts\apply_model_profile.py current

# 国产模型适配配置
.\.venv\Scripts\python.exe .\scripts\apply_model_profile.py china
```

`current` 保持现在的 Codex/SpatialAI + OpenRouter embedding 链路；`china` 切到 OpenCode/OpenRouter 中转里的国产模型：Qwen、Mimo 和 Qwen embedding。切换脚本只更新 provider/model 路由，不写入或输出任何 API key。

当前实测可用编排：

```env
MODEL_PROFILE=current
ACTIVE_MODEL_PROVIDER=codex

# SpatialAI Codex/OpenAI-compatible line.
OPENAI_BASE_URL=https://spatialai.vip/v1
OPENAI_API_KEY=
OPENAI_TEXT_MODEL=gpt-5.5
OPENAI_VISION_MODEL=gpt-5.5
OPENAI_EMBEDDING_MODEL=
CODEX_BASE_URL=https://spatialai.vip/v1
CODEX_API_KEY=
CODEX_TEXT_MODEL=gpt-5.5
CODEX_VISION_MODEL=gpt-5.5
CODEX_EMBEDDING_MODEL=

OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b

OPENCODE_BASE_URL=https://opencode.ai/zen/go/v1
OPENCODE_API_KEY=
OPENCODE_TEXT_MODEL=qwen3.6-plus
OPENCODE_VISION_MODEL=mimo-v2-omni
OPENCODE_EMBEDDING_MODEL=

ANTHROPIC_BASE_URL=https://spatialai.vip
ANTHROPIC_AUTH_TOKEN=
ANTHROPIC_MODEL=claude-opus-4-6

TEXT_AGENT_PROVIDER=codex
TEXT_AGENT_MODEL=gpt-5.5
VISION_AGENT_PROVIDER=codex
VISION_AGENT_MODEL=gpt-5.5
EMBEDDING_AGENT_PROVIDER=openrouter
EMBEDDING_AGENT_MODEL=qwen/qwen3-embedding-8b
COMPLIANCE_AGENT_PROVIDER=codex
COMPLIANCE_AGENT_MODEL=gpt-5.5
KNOWLEDGE_AGENT_PROVIDER=codex
KNOWLEDGE_AGENT_MODEL=gpt-5.5
```

本机探测到 SpatialAI Codex 线暴露了 `gpt-5.5`、`gpt-5.4`、`gpt-5.3-codex` 等模型，其中 `gpt-5.5`、`gpt-5.4`、`gpt-5.3-codex` 的文本调用已通过冒烟测试。`gpt-5.5` 使用正常尺寸图片时也已通过多模态 caption 测试，因此文本、合规、知识沉淀和视觉都默认走 Codex 线。OpenCode/Zen 的 `mimo-v2-omni` 保留为视觉备用。

这里的 `ANTHROPIC_AUTH_TOKEN` 是 SpatialAI 的 Claude/Anthropic-compatible key，走 `ANTHROPIC_BASE_URL=https://spatialai.vip`；`OPENAI_API_KEY` 是 SpatialAI 的 Codex/OpenAI-compatible key，走 `OPENAI_BASE_URL=https://spatialai.vip/v1`，项目内也同步到 `CODEX_API_KEY` 作为更清晰的别名。Claude key 可以列出模型，但普通 HTTP 生成会被中转站返回 `Client not allowed`，因此默认不路由到本项目后端。embedding 默认走 OpenRouter 的 `qwen/qwen3-embedding-8b`，失败时后端会回退到本地 hash embedding。

安全写入 OpenRouter key：

```powershell
.\scripts\set_openrouter_key.ps1
```

## 模型探测

只看 provider、角色路由和 `/models` 列表，不打印 key：

```powershell
.\.venv\Scripts\python.exe .\scripts\probe_models.py
```

对当前角色路由跑最小生成/embedding 冒烟测试：

```powershell
.\.venv\Scripts\python.exe .\scripts\smoke_models.py
.\.venv\Scripts\python.exe .\scripts\smoke_models.py --embedding-provider openrouter --embedding-model qwen/qwen3-embedding-8b
```

测试某个 OpenCode 或 SpatialAI Codex 中转模型名是否能被调用：

```powershell
.\.venv\Scripts\python.exe .\scripts\smoke_models.py --provider opencode --model <model-id> --role text
.\.venv\Scripts\python.exe .\scripts\smoke_models.py --provider codex --model gpt-5.5 --role text
```

如果 `/models` 返回 401/403，不一定代表 base URL 错，也可能是中转站不开放模型列表接口。最终以 `smoke_models.py` 的最小生成请求为准。

## 数据入库与索引

把维修手册放入：

```text
data/raw/manuals
```

支持 `.pdf`、`.txt`、`.md`，包括子目录。公开资料来源清单在：

```text
data/sources/public_manual_sources.json
```

先验证公开 URL，再下载到本地：

```powershell
.\.venv\Scripts\python.exe .\scripts\validate_public_sources.py
.\.venv\Scripts\python.exe .\scripts\download_public_sources.py --required-only
```

下载的 PDF 会带 `*.source.json` 元数据，入库时会保留来源 URL、许可说明和版本。启动服务后可在“资源与模型”页触发：

- 入库手册
- 重建索引
- 生成样例
- 运行评测
- 探测模型

也可以直接调用 API：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/admin/ingest-manuals -Method Post
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/admin/rebuild-index -Method Post
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/admin/generate-sample-data -Method Post
Invoke-RestMethod -Uri "http://127.0.0.1:8051/api/eval/run?max_questions=20" -Method Post
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/review-status
```

`max_questions=20` 用于演示快速评测；正式报告可以去掉该参数跑完整评测。若机械审核包尚未回写，评测结果会标记为 `review_basis=unreviewed_fallback`；有已审核评测题后，会自动优先使用 `review_status='approved'` 的题目。

## 机械审核包

生成 120 条案例和 100 条评测问答后，导出给机械专业队友审核：

```powershell
.\.venv\Scripts\python.exe .\scripts\export_review_pack.py
```

审核后回写：

```powershell
.\.venv\Scripts\python.exe .\scripts\import_review_pack.py
```

审核进度检查：

```powershell
.\.venv\Scripts\python.exe .\scripts\review_progress.py
```

审核标准见 [docs/MECHANICAL_REVIEW_GUIDE.md](docs/MECHANICAL_REVIEW_GUIDE.md)，当前进度报告见 [docs/MECHANICAL_REVIEW_STATUS.md](docs/MECHANICAL_REVIEW_STATUS.md)。

## 参赛提交包

正式提交/开源时不要直接打包 `.env.local`、SQLite 运行库、下载的公开 PDF、上传图片和缓存目录。使用下面脚本生成许可证更安全的源码与文档包：

```powershell
.\.venv\Scripts\python.exe .\scripts\build_submission_package.py
```

输出位于 `dist/a1-maintenance-assistant-submission-<时间>.zip`。包内保留源码、前端、测试、文档、`.env.example`、公开资料来源清单、PDF sidecar metadata 和机械审核 CSV；不再分发原始 PDF，只保留来源 URL 和许可说明，便于答辩引用和现场重新下载。

## 完成度审计

生成提交包后，可以运行可重复审计脚本，检查真实资料、索引、模型路由、审核包、提交包禁入文件，以及机械审核和 LoongArch 实机缺口：

```powershell
.\.venv\Scripts\python.exe .\scripts\audit_readiness.py --submission-archive .\dist\a1-maintenance-assistant-submission-<时间>.zip
```

脚本会写出 `docs/READINESS_AUDIT.md`。只要机械审核或 LoongArch 实机验证没完成，结果会保持 `ready=false`，避免把开发环境验证误当成正式参赛完成。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe .\scripts\check_deploy.py
```

## 目录

```text
backend/app/       FastAPI 后端、检索、SOP、合规、图谱、模型路由
frontend/          Vue 3 静态工作台
data/              SQLite 数据库、原始手册、上传图片
scripts/           启动、环境模板、模型探测、部署检查、审核包与提交包脚本
tests/             API 回归测试
docs/              数据来源、机械审核、资源缺口、LoongArch 部署说明、完成度审计
```

作品说明书见 [docs/WORK_DESCRIPTION.md](docs/WORK_DESCRIPTION.md)，技术架构说明见 [docs/TECHNICAL_ARCHITECTURE.md](docs/TECHNICAL_ARCHITECTURE.md)，测试报告见 [docs/TEST_REPORT.md](docs/TEST_REPORT.md)，授权与引用说明见 [docs/LICENSE_AND_ATTRIBUTION.md](docs/LICENSE_AND_ATTRIBUTION.md)，答辩演示流程见 [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)，PPT 大纲见 [docs/PPT_OUTLINE.md](docs/PPT_OUTLINE.md)，最终提交检查清单见 [docs/FINAL_SUBMISSION_CHECKLIST.md](docs/FINAL_SUBMISSION_CHECKLIST.md)。

剩余外部资源和队友分工见 [docs/ACTION_ITEMS_FOR_USER.md](docs/ACTION_ITEMS_FOR_USER.md)。

PPT 初稿位于 `materials/A1-maintenance-assistant-defense.pptx`。如需重新生成：

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\.venv\Scripts\python.exe .\scripts\build_ppt.py
```

作品说明书 DOCX 初稿位于 `materials/A1-maintenance-assistant-work-description.docx`。如需重新生成：

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\.venv\Scripts\python.exe .\scripts\build_docx.py
```

LoongArch 现场验收报告可在目标机生成：

```powershell
.\.venv\Scripts\python.exe .\scripts\loongarch_acceptance.py --api-base-url http://127.0.0.1:8051
```

最终综合验证：

```powershell
.\.venv\Scripts\python.exe .\scripts\final_validation.py --submission-archive .\dist\a1-maintenance-assistant-submission-20260510-readiness-final.zip --api-base-url http://127.0.0.1:8051
```
