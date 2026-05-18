# A1 Readiness Audit

Ready: `True`
Deployment mode: `public`

## Checks

| Check | Status | Evidence |
|---|---|---|
| `web_system` | `pass` | FastAPI backend and Vue static frontend files are present. |
| `public_sources` | `pass` | 9 active public sources; equipment=['bearing', 'motor', 'pump']. |
| `document_index` | `pass` | 12 manual chunks; 0 have source URLs. |
| `cloud_model_routes` | `pass` | 5 remote role routes are supported with keys. |
| `openrouter_embedding` | `pass` | {'role': 'embedding', 'label': '向量检索', 'provider': 'openrouter', 'kind': 'embeddings', 'base_url': 'https://openrouter.ai/api/v1', 'key_present': True, 'model': 'qwen/qwen3-embedding-8b', 'supported': True} |
| `case_and_eval_assets` | `pass` | review CSV rows: cases=158, eval_questions=134. |
| `mechanical_review` | `pass` | approved cases=159/150; approved eval=134/130; unreviewed cases=2, eval=0. |
| `submission_package` | `pass` | exists=True; entries=193; forbidden=0. |
| `image_eval_assets` | `pass` | rows=30; available=30/30; approved=30/30; missing=0. |
| `public_demo_deployment` | `pass` | public_doc=True; supabase_schema=True; render_yaml=True; cloudflare_script=True. |
| `loongarch_runtime` | `blocked` | current platform=Windows-11-10.0.26200-SP0, machine=AMD64. |

## Missing Resources

- None

## Summary

```json
{
  "db_path": "D:\\30726\\Desktop\\竞赛目录\\a1-maintenance-assistant\\data\\maintenance.db",
  "documents": 0,
  "manual_chunks": 12,
  "chunks_with_source_url": 0,
  "cases_total": 161,
  "cases_approved": 159,
  "cases_unreviewed": 2,
  "eval_total": 134,
  "eval_approved": 134,
  "eval_unreviewed": 0,
  "visual_assets": 30,
  "approved_visual_assets": 30,
  "embedding_models": {},
  "active_public_sources": 9,
  "public_source_equipment": [
    "bearing",
    "motor",
    "pump"
  ],
  "review_case_rows": 158,
  "review_eval_rows": 134,
  "image_eval_rows": 30,
  "image_eval_available": 30,
  "image_eval_approved": 30,
  "image_eval_missing": 0,
  "submission_entries": 193,
  "submission_forbidden_entries": 0
}
```
