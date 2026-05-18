# A1-MAKG Upgrade Notes

Updated: 2026-05-12

## Summary

This upgrade turns the project into an A1-MAKG prototype: a multimodal, agentic, knowledge-graph-assisted maintenance retrieval and work-assistance system.

The main change is not a framework rewrite. The existing FastAPI, Vue, SQLite, hybrid retrieval, SOP, compliance, case review, and evaluation panel remain the foundation. The upgrade adds an official sample manual path, external reference verification, graph-enhanced evidence, visual evidence, work-order status, and hard evaluation samples.

## Official A1 Sample Manual

The official sample file provided by the user is:

`D:/30726/Desktop/竞赛目录/摩托车发动机维修手册.pdf`

It is copied into the local raw-manual area as:

`data/raw/manuals/official/motorcycle-engine-maintenance-manual.pdf`

The sidecar metadata is:

`data/raw/manuals/official/motorcycle-engine-maintenance-manual.pdf.source.json`

Verification checks:

- Expected page count: 41.
- Expected keywords: `摩托车发动机维修手册`, `火花塞`, `起动电机`, `发动机`, `压缩压力`.
- PDF text extraction must work.
- Page 1 must render through Poppler when `pdftoppm` is available.
- The resource is marked as `official_sample_manual`.

Redistribution note: the original PDF is treated as a contest-provided local sample. Do not publish it unless contest rules explicitly allow redistribution.

## External Resource Verification

Reference manifest:

`data/sources/external_reference_resources.json`

Generated verification report:

- `data/sources/verified_resources.json`
- `docs/EXTERNAL_RESOURCE_VERIFICATION.md`

The verifier downloads or records only license-safe reference material:

- GitHub projects: metadata, README, LICENSE, commit/default-branch metadata.
- Papers: official PDF or official article page when accessible.
- Dataset/project pages: HTML page only, not full datasets.

Blocked resources are not used as verified evidence. During the latest run, ScienceDirect pages for MAKG and MllmDA-KGC were blocked by HTTP 403, so they remain reference ideas only and are not treated as downloaded proof.

Run:

```powershell
.\.venv\Scripts\python.exe .\scripts\verify_external_resources.py
```

## System Behavior Changes

The device dictionary now includes `engine` as an official sample device. The main competition narrative still focuses on electric motors, centrifugal pumps, and bearings.

`/api/query` now returns additional evidence fields:

- `graph_paths`: equipment-component-fault-SOP-compliance paths derived from retrieved evidence.
- `visual_evidence`: uploaded image caption plus visual manual chunks when available.
- `resource_verification_summary`: verified resource count and official sample status.

Manual citations now also expose:

- `modality`
- `image_caption`

Maintenance cases now include work-order status:

- `pending_review`
- `archived`
- `archived_in_graph`

Approving a case moves it to `archived_in_graph` and writes knowledge-graph nodes/edges as before.

## A1-MAKG Data Additions

The upgrade adds:

- 3 engine maintenance cases, including 2 approved official-sample cases and 1 pending work-order case.
- 30 hard evaluation questions prefixed with `A1-HARD-`.
- Engine graph nodes for motorcycle engine, spark plug, compression pressure, water pump, and anti-misstart safety.

Apply upgrade data and ingest manuals without rebuilding embeddings:

```powershell
.\.venv\Scripts\python.exe .\scripts\apply_a1_makg_upgrade.py
```

The script intentionally skips embedding rebuild to avoid long remote embedding runs for the official PDF. Retrieval still works through BM25 and metadata scoring. If a final full-index refresh is needed, use the Web admin rebuild control or call `/api/admin/rebuild-index` after the backend is running.

## LoongArch Status

No LoongArch remote server is available in this stage. The project must not claim real LoongArch execution.

Current status:

- LoongArch-ready deployment documentation and acceptance scripts are retained.
- Public/cloud and local demonstrations remain the verified paths.
- Final defense materials should state: real LoongArch validation is pending official remote environment access.

## Verification

Recommended checks after this upgrade:

```powershell
.\.venv\Scripts\python.exe .\scripts\verify_external_resources.py --no-download
.\.venv\Scripts\python.exe .\scripts\apply_a1_makg_upgrade.py
.\.venv\Scripts\python.exe -m pytest -q
```

The final package must still exclude secrets, runtime databases, unlicensed PDFs, caches, and generated large artifacts.
