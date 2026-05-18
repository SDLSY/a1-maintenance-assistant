# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A1-MAKG：面向设备检修的多模态证据链作业辅助系统。中国软件杯 A1 赛题原型，聚焦电机、离心泵、轴承和发动机四类设备，核心流程：多模态检索 → SOP 生成 → 合规校验 → 案例沉淀 → 知识图谱更新。

## Commands

### Start server (local dev)
```powershell
cd D:\30726\Desktop\竞赛目录\a1-maintenance-assistant
.\scripts\run_server.ps1
# 浏览器访问 http://127.0.0.1:8051
```

Or directly with uvicorn:
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8051 --reload
```

### Run tests
```powershell
.\.venv\Scripts\python.exe -m pytest
# Run a single test file
.\.venv\Scripts\python.exe -m pytest tests/test_api.py
```

### Model probing and smoke tests
```powershell
.\.venv\Scripts\python.exe .\scripts\probe_models.py
.\.venv\Scripts\python.exe .\scripts\smoke_models.py
```

### Switch model profile
```powershell
.\.venv\Scripts\python.exe .\scripts\apply_model_profile.py current   # Codex/SpatialAI
.\.venv\Scripts\python.exe .\scripts\apply_model_profile.py china      # Qwen/Mimo
.\.venv\Scripts\python.exe .\scripts\apply_model_profile.py --list
```

### Data pipeline
```powershell
# Ingest manuals from data/raw/manuals
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/admin/ingest-manuals -Method Post
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/admin/rebuild-index -Method Post
Invoke-RestMethod -Uri http://127.0.0.1:8051/api/admin/generate-sample-data -Method Post
# Quick eval (20 questions)
Invoke-RestMethod -Uri "http://127.0.0.1:8051/api/eval/run?max_questions=20" -Method Post
```

### Submission package
```powershell
.\.venv\Scripts\python.exe .\scripts\build_submission_package.py
.\.venv\Scripts\python.exe .\scripts\audit_readiness.py --submission-archive .\dist\<archive>.zip
```

### Public deployment (Cloudflare Pages + Render)
```powershell
.\.venv\Scripts\python.exe .\scripts\prepare_cloudflare_site.py --api-base-url https://<backend-domain> --output-dir .\dist\cloudflare-site
# Render start command: python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

## Architecture

### Backend (`backend/app/`)

FastAPI app, all routes in `main.py`. Key modules:

| Module | Role |
|---|---|
| `settings.py` | Reads `.env.local` / `.env`; exposes `settings` singleton with per-role provider/model routing |
| `model_gateway.py` | Unified call surface for all LLM providers (openai, codex, opencode, openrouter, spatialai/anthropic); `generate_text()` is the primary entry point |
| `agents.py` | Builds SOP, model-review prompt, and agent trace; calls `model_gateway.generate_text()` |
| `retrieval.py` | BM25+embedding hybrid retrieval over `manual_chunks` and `maintenance_cases` tables |
| `vector_index.py` | Builds/rebuilds embedding index; falls back to hash-based embeddings when remote fails |
| `database.py` | SQLite connection, schema init, seed data bootstrap; `DB_PATH` = `data/maintenance.db` |
| `graph_store.py` | Knowledge graph backend abstraction; SQLite fallback by default, Neo4j optional |
| `spatial_guidance.py` | 3D component highlighting and spatial context generation |
| `visual_analysis.py` | Image caption/analysis via vision models; saves to `visual_assets` table |
| `candidate_cad.py` | CAD candidate lifecycle (create, patch, render, review, promote) |
| `cad_pipeline/` | OpenSCAD/FreeCAD toolchain for converting CAD to GLB |
| `supabase_sync.py` | Optional sync of cases and feedback to Supabase for public deployment |
| `evaluation.py` | Evaluation runner and metrics; uses `eval_questions` table |
| `workflow.py` | Tri-MRO alignment and workflow state aggregation |

### Frontend (`frontend/`)

Vanilla HTML/JS + minimal vendor libs (Three.js for 3D workbench). No build step needed — served directly as static files by FastAPI. Main entry: `index.html` / `app.js`. Marketing page: `marketing.html`.

### Data layer

- **Primary store**: SQLite (`data/maintenance.db`) — documents, manual_chunks, maintenance_cases, feedback, kg_nodes, kg_edges, visual_assets, eval_questions, 3d_models, cad_candidates
- **Optional cloud sync**: Supabase (mutable tables only: cases, feedback, review status)
- **Manual ingestion**: PDFs/TXT/MD placed in `data/raw/manuals/`, ingested via `/api/admin/ingest-manuals`
- **3D assets**: `data/3d/authorized_models/` (licensed), `data/3d/public/` (served at `/3d-assets/`)

### Model routing

`Settings.provider_for_role(role)` maps each of five agent roles (text, vision, embedding, compliance, knowledge) to a named provider. `model_gateway.generate_text()` dispatches to the correct provider using that mapping. Providers are all OpenAI-compatible HTTP APIs except `spatialai` which uses Anthropic-compatible format. Embedding falls back to local hash-based vectors if the remote provider fails.

### Environment

`.env.local` (not `.env`) is loaded first. The file has two layers:
1. Credential layer: `*_BASE_URL` and `*_API_KEY` per provider
2. Role routing layer: `TEXT_AGENT_PROVIDER`, `VISION_AGENT_PROVIDER`, etc.

Copy `.env.example` to `.env.local` and fill in keys. Use `scripts/set_openrouter_key.ps1` to safely write the OpenRouter key.

## Key constraints

- The graph backend defaults to SQLite. Set `GRAPH_BACKEND=neo4j` with `NEO4J_URI/USER/PASSWORD` to switch.
- `REMOTE_QUERY_EMBEDDING_ENABLED=false` by default — only document ingestion uses remote embeddings; query-time uses local hash vectors unless explicitly enabled.
- Submission packages must exclude `.env.local`, downloaded PDFs, SQLite DB, and upload cache. Use `build_submission_package.py`.
- Readiness audit (`audit_readiness.py`) stays `ready=false` until mechanical review and LoongArch on-site verification are complete.
