# Final Validation Report

ready: `True`
deployment_mode: `public`

## Blockers

- None

## Summary

| Area | Status |
|---|---|
| readiness | `True` |
| review_csv_goal | `True` |
| loongarch_acceptance | `False` |
| submission_forbidden_entries | `0` |

## Raw Result

```json
{
  "ready": true,
  "deployment_mode": "public",
  "blockers": [],
  "readiness": {
    "ready": true,
    "checks": {
      "web_system": "pass",
      "public_sources": "pass",
      "document_index": "pass",
      "cloud_model_routes": "pass",
      "openrouter_embedding": "pass",
      "case_and_eval_assets": "pass",
      "mechanical_review": "pass",
      "submission_package": "pass",
      "image_eval_assets": "pass",
      "public_demo_deployment": "pass",
      "loongarch_runtime": "blocked"
    },
    "missing_resources": []
  },
  "review": {
    "ready_for_goal": true,
    "cases_approved": 156,
    "eval_approved": 134,
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
    "submission_entries": 193,
    "submission_forbidden_entries": 0
  }
}
```
