# LoongArch + 银河麒麟部署说明

目标环境只部署 Web、SQLite、索引和编排服务。大模型推理、视觉 caption 和 embedding 默认走云端 API。

## 环境要求

- Python 3.10+
- pip
- 可访问模型中转站或 OpenAI-compatible API
- SQLite 可用
- 允许监听本机端口，例如 8051

## 部署步骤

```bash
cd a1-maintenance-assistant
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env.local
python scripts/download_public_sources.py --required-only
python scripts/check_deploy.py
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8051
```

如果使用参赛提交包部署，包内不会包含原始 PDF 和 SQLite 运行库。解压后需要在目标机上重新下载公开资料、入库并重建索引：

```bash
python scripts/download_public_sources.py --required-only
curl -X POST http://127.0.0.1:8051/api/admin/ingest-manuals
curl -X POST http://127.0.0.1:8051/api/admin/rebuild-index
```

## 当前推荐配置

在 `.env.local` 中设置，不要把真实 key 写入提交包：

```env
ACTIVE_MODEL_PROVIDER=codex

CODEX_BASE_URL=https://spatialai.vip/v1
CODEX_API_KEY=本地填写
CODEX_TEXT_MODEL=gpt-5.5
CODEX_VISION_MODEL=gpt-5.5

OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=本地填写
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b

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

兼容旧 OpenAI-compatible 中转时，也可以把同一个 Codex key 写入 `OPENAI_API_KEY` / `OPENAI_BASE_URL`，但最终角色路由以 `TEXT_AGENT_PROVIDER` 等变量为准。

如果答辩现场需要展示国产模型适配链路，可以在目标机填写 `OPENCODE_API_KEY` 与 `OPENROUTER_API_KEY` 后执行：

```bash
python scripts/apply_model_profile.py china
python scripts/check_deploy.py
python scripts/smoke_models.py
```

这会切换到 `opencode / qwen3.6-plus`、`opencode / mimo-v2-omni` 和 `openrouter / qwen/qwen3-embedding-8b`。该配置强调国产模型能力；应用、数据库、索引和编排服务仍然在本机或 LoongArch + 银河麒麟环境运行。

## 验证

```bash
python scripts/check_deploy.py
python -m pytest
curl http://127.0.0.1:8051/api/health
curl http://127.0.0.1:8051/api/agent-routing
curl -X POST http://127.0.0.1:8051/api/admin/rebuild-index
curl -X POST "http://127.0.0.1:8051/api/eval/run?max_questions=20"
```

`scripts/check_deploy.py` 在 LoongArch 机器上应显示 `loongarch_like: true` 或 `machine` 中包含 LoongArch 字样；在当前 Windows/AMD64 开发机上该项会是 false，只能算本地兼容性检查。

生成现场验收报告：

```bash
python scripts/loongarch_acceptance.py --api-base-url http://127.0.0.1:8051
```

报告输出到：

```text
docs/LOONGARCH_ACCEPTANCE_REPORT.md
```

只有在 LoongArch + 银河麒麟目标机上运行，且 API 连通时，`loongarch_validated` 才应为 `true`。

最终提交前必须录屏证明系统在 LoongArch + 银河麒麟环境中完成：启动、检索、图片上传、SOP 生成、案例审核、图谱更新和评测运行。
