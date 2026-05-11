# Multimodal Image Evaluation Assets

This directory tracks the image set required for the A1 multimodal evaluation. The repository intentionally stores only the manifest and status report. Real images are not bundled in the submission archive because they may contain third-party copyright or field-site information.

## Required Scope

- Minimum: 30 reviewed fault images.
- Equipment coverage: electric motor, centrifugal pump, rolling bearing.
- Each image must map to one row in `fault_image_eval_manifest.csv`.
- Each row must include expected retrieval keywords and expected safety keywords so the team can evaluate caption quality, retrieval hit rate, and SOP safety coverage.

## Image Intake Rules

Place authorized local files under:

```text
data/image_eval/images/
```

Acceptable sources:

- Self-captured lab or workshop photos with school/team authorization.
- Public industrial defect datasets whose license permits academic competition demonstration.
- Vendor or manual images only when redistribution and presentation are explicitly allowed.

After adding images, update the row:

- `review_status`: `approved` after the mechanical reviewer accepts the image and labels.
- `reviewer`: use reviewer code such as `ME-R01`, not a real name.
- `review_notes`: short note about the visible evidence and source decision.

Then run:

```powershell
.\.venv\Scripts\python.exe .\scripts\image_eval_status.py
```

The target status is:

```text
ready=true
available_images>=30
approved_images>=30
```
