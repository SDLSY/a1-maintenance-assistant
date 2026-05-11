# Final Validation Report

ready: `False`
deployment_mode: `public`

## Blockers

- `image_eval_assets`

## Summary

| Area | Status |
|---|---|
| readiness | `False` |
| review_csv_goal | `True` |
| loongarch_acceptance | `False` |
| submission_forbidden_entries | `0` |

## Raw Result

```json
{
  "ready": false,
  "deployment_mode": "public",
  "blockers": [
    "image_eval_assets"
  ],
  "readiness": {
    "ready": false,
    "checks": {
      "web_system": "pass",
      "public_sources": "pass",
      "document_index": "pass",
      "cloud_model_routes": "pass",
      "openrouter_embedding": "pass",
      "case_and_eval_assets": "pass",
      "mechanical_review": "pass",
      "submission_package": "pass",
      "image_eval_assets": "blocked",
      "public_demo_deployment": "pass",
      "loongarch_runtime": "blocked"
    },
    "missing_resources": [
      "Need 30 authorized and mechanically approved fault images under data/image_eval/images/ for the multimodal image evaluation gate."
    ]
  },
  "review": {
    "ready_for_goal": true,
    "cases_approved": 125,
    "eval_approved": 104,
    "missing": []
  },
  "loongarch": {
    "loongarch_validated": false,
    "checks": {
      "platform": "blocked",
      "python_modules": "pass",
      "database": "pass",
      "model_routes": "pass",
      "api": "pass"
    }
  },
  "submission": {
    "submission_entries": 108,
    "submission_forbidden_entries": 0
  }
}
```
