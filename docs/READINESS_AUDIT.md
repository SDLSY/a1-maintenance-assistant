# A1 Readiness Audit

Ready: `False`
Deployment mode: `public`

## Checks

| Check | Status | Evidence |
|---|---|---|
| `web_system` | `pass` | FastAPI backend and Vue static frontend files are present. |
| `public_sources` | `pass` | 9 active public sources; equipment=['bearing', 'motor', 'pump']. |
| `document_index` | `pass` | 1108 manual chunks; 1092 have source URLs. |
| `cloud_model_routes` | `pass` | 5 remote role routes are supported with keys. |
| `openrouter_embedding` | `pass` | {'role': 'embedding', 'label': '向量检索', 'provider': 'openrouter', 'kind': 'embeddings', 'base_url': 'https://openrouter.ai/api/v1', 'key_present': True, 'model': 'qwen/qwen3-embedding-8b', 'supported': True} |
| `case_and_eval_assets` | `pass` | review CSV rows: cases=125, eval_questions=104. |
| `mechanical_review` | `pass` | approved cases=125/100; approved eval=104/100; unreviewed cases=0, eval=0. |
| `submission_package` | `pass` | exists=True; entries=108; forbidden=0. |
| `image_eval_assets` | `blocked` | rows=30; available=0/30; approved=0/30; missing=30. |
| `public_demo_deployment` | `pass` | public_doc=True; supabase_schema=True; render_yaml=True; cloudflare_script=True. |
| `loongarch_runtime` | `blocked` | current platform=Windows-11-10.0.26200-SP0, machine=AMD64. |

## Missing Resources

- Need 30 authorized and mechanically approved fault images under data/image_eval/images/ for the multimodal image evaluation gate.

## Summary

```json
{
  "db_path": "D:\\30726\\Desktop\\竞赛目录\\a1-maintenance-assistant\\data\\maintenance.db",
  "documents": 13,
  "manual_chunks": 1108,
  "chunks_with_source_url": 1092,
  "cases_total": 125,
  "cases_approved": 125,
  "cases_unreviewed": 0,
  "eval_total": 104,
  "eval_approved": 104,
  "eval_unreviewed": 0,
  "embedding_models": {
    "qwen/qwen3-embedding-8b": 1233
  },
  "active_public_sources": 9,
  "public_source_equipment": [
    "bearing",
    "motor",
    "pump"
  ],
  "review_case_rows": 125,
  "review_eval_rows": 104,
  "image_eval_rows": 30,
  "image_eval_available": 0,
  "image_eval_approved": 0,
  "image_eval_missing": 30,
  "submission_entries": 108,
  "submission_forbidden_entries": 0
}
```
