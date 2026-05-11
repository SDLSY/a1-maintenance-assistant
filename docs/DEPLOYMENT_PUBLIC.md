# 公网演示部署说明：Cloudflare Pages + Render + Supabase

当前阶段先把国产化实机部署放到后面，公网演示采用方案 B：

- Cloudflare Pages：托管静态 Vue 前端。
- Render：托管 FastAPI 后端。
- Supabase：持久化“可变数据”，包括一线案例、审核状态和人工修正。
- SQLite：继续作为后端本地检索库和索引缓存，保存手册 chunk、评测集、知识图谱基础数据和向量索引。

## Supabase

1. 新建 Supabase project。
2. 打开 SQL editor，执行 [SUPABASE_SCHEMA.sql](SUPABASE_SCHEMA.sql)。
3. 在后端平台只配置服务端环境变量：

```env
SUPABASE_ENABLED=true
SUPABASE_URL=https://<project-ref>.supabase.co
# 兼容旧 Next/Supabase 项目命名：NEXT_PUBLIC_SUPABASE_URL 也会被后端识别。
SUPABASE_SECRET_KEY=<server-only>
# 旧项目也可以使用 SUPABASE_SERVICE_ROLE_KEY=<server-only>
SUPABASE_SCHEMA=public
SUPABASE_TABLE_PREFIX=a1_
SUPABASE_SYNC_ON_STARTUP=true
```

不要把 `SUPABASE_SECRET_KEY` 或 `SUPABASE_SERVICE_ROLE_KEY` 放到 Cloudflare Pages、浏览器代码、PPT 或提交包里。前端不直接访问 Supabase。`SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` 只能作为浏览器匿名 key，不能开启后端同步。

当前实现策略是“SQLite + Supabase 镜像”：

- 手册、chunk、embedding、评测题仍由 SQLite 支撑，保证检索速度和本地演示稳定。
- 新增案例、案例审核、人工修正会写入 SQLite 后自动镜像到 Supabase。
- 后端启动时会从 Supabase 拉回案例和人工修正，免费平台重启后不会丢演示中产生的业务记录。
- 如需手动同步，调用：

```bash
curl -X POST https://<backend-domain>/api/admin/sync-supabase
```

## Render 后端

仓库已提供 [render.yaml](../render.yaml)。Render Web Service 的核心配置：

```text
Build Command: pip install -r requirements.txt
Start Command: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

必须在 Render 环境变量中配置：

```env
ACTIVE_MODEL_PROVIDER=codex
CORS_ALLOWED_ORIGINS=https://<your-cloudflare-pages-domain>

SUPABASE_ENABLED=true
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=<server-only>
SUPABASE_SCHEMA=public
SUPABASE_TABLE_PREFIX=a1_

CODEX_BASE_URL=https://spatialai.vip/v1
CODEX_API_KEY=<server-only>
CODEX_TEXT_MODEL=gpt-5.5
CODEX_VISION_MODEL=gpt-5.5

OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=<server-only>
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

如果先用本地兜底模型演示，可以把 `TEXT_AGENT_PROVIDER` 等临时设为 `local`，但答辩前建议恢复云端模型链。

## Cloudflare Pages 前端

前端不是 Node/Vite 项目，是纯静态 Vue。先生成 Cloudflare 可部署目录：

```bash
python scripts/prepare_cloudflare_site.py \
  --api-base-url https://<backend-domain> \
  --output-dir dist/cloudflare-site
```

Cloudflare Pages 配置：

```text
Build command: python scripts/prepare_cloudflare_site.py --api-base-url https://<backend-domain>
Build output directory: dist/cloudflare-site
```

生成结果会把 `frontend/index.html` 放到根目录，把 `app.js`、`styles.css`、`vendor/` 和 `config.js` 放到 `/static/`，兼容现有 HTML 路径。

如果使用 Supabase CLI，也可以把迁移文件目录 `supabase/migrations/` 推到项目；当前等价 SQL 同时保留在 [SUPABASE_SCHEMA.sql](SUPABASE_SCHEMA.sql)。

## 验证

后端：

```bash
curl https://<backend-domain>/api/health
curl https://<backend-domain>/api/providers
curl -X POST https://<backend-domain>/api/admin/sync-supabase
curl -X POST "https://<backend-domain>/api/eval/run?max_questions=4"
```

前端：

```text
打开 Cloudflare Pages 域名
刷新页面应能看到 health.status = ok
提交一条案例，审核入库
重启 Render 服务后，调用 sync-supabase，案例仍可恢复
```

本阶段放弃国产化实机时，审计脚本使用 public 模式：

```bash
python scripts/audit_readiness.py \
  --deployment-mode public \
  --submission-archive dist/a1-maintenance-assistant-submission-<timestamp>.zip

python scripts/final_validation.py \
  --deployment-mode public \
  --submission-archive dist/a1-maintenance-assistant-submission-<timestamp>.zip \
  --api-base-url https://<backend-domain>
```

## 仍然不覆盖的内容

这个方案解决公网演示和可变数据持久化，但不等于国产化部署验证。参赛材料里应写：

```text
公网演示环境：Cloudflare Pages + Render + Supabase
国产化部署验证：后续在鲲鹏/openEuler 或银河麒麟环境补充
```
