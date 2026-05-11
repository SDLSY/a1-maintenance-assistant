# LoongArch Acceptance Report

loongarch_validated: `False`

## Checks

| Check | Status | Evidence |
|---|---|---|
| `platform` | `blocked` | platform=Windows-11-10.0.26200-SP0; machine=AMD64 |
| `python_modules` | `pass` | {"fastapi": true, "uvicorn": true, "pypdf": true, "sqlite3": true} |
| `database` | `pass` | {"db_path": "D:\\30726\\Desktop\\竞赛目录\\a1-maintenance-assistant\\data\\maintenance.db", "documents": 13, "manual_chunks": 1108, "cases": 125, "eval_questions": 104, "embedding_rows": 1233} |
| `model_routes` | `pass` | [{"role": "text", "label": "诊断与SOP", "provider": "codex", "kind": "openai-compatible", "base_url": "https://spatialai.vip/v1", "key_present": true, "model": "gpt-5.5", "supported": true}, {"role": "vision", "label": "图片描述", "provider": "codex", "kind": "openai-compatible", "base_url": "https://spatialai.vip/v1", "key_present": true, "model": "gpt-5.5", "supported": true}, {"role": "embedding", "label": "向量检索", "provider": "openrouter", "kind": "embeddings", "base_url": "https://openrouter.ai/api/v1", "key_present": true, "model": "qwen/qwen3-embedding-8b", "supported": true}, {"role": "compliance", "label": "合规复核", "provider": "codex", "kind": "openai-compatible", "base_url": "https://spatialai.vip/v1", "key_present": true, "model": "gpt-5.5", "supported": true}, {"role": "knowledge", "label": "知识沉淀", "provider": "codex", "kind": "openai-compatible", "base_url": "https://spatialai.vip/v1", "key_present": true, "model": "gpt-5.5", "supported": true}] |
| `api` | `pass` | base_url=http://127.0.0.1:8051; ok=True |

## Platform

```json
{
  "python": "3.12.7",
  "platform": "Windows-11-10.0.26200-SP0",
  "machine": "AMD64",
  "loongarch_like": false,
  "sqlite": "3.45.3"
}
```

## Database

```json
{
  "db_path": "D:\\30726\\Desktop\\竞赛目录\\a1-maintenance-assistant\\data\\maintenance.db",
  "documents": 13,
  "manual_chunks": 1108,
  "cases": 125,
  "eval_questions": 104,
  "embedding_rows": 1233
}
```

## Next Steps

- 在 LoongArch + 银河麒麟机器运行本脚本。
- 启动 8051 服务后带默认 API URL 运行，确认 api=pass。
- 按 docs/DEMO_SCRIPT.md 录屏文本问诊、图片上传、案例审核、图谱更新和评测。
