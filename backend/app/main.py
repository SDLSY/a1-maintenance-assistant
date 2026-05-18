from __future__ import annotations

import html
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .agents import agent_trace, build_model_review_prompt, build_sop
from .candidate_cad import (
    create_candidate_from_visual_asset,
    get_candidate_asset,
    list_candidate_assets,
    patch_candidate_spec,
    regenerate_candidate_artifacts,
    resolve_candidate_file,
    review_candidate_asset,
    save_candidate_promotion,
)
from .cad_pipeline.promotion import promote_candidate_to_model
from .cad_pipeline.runtime import probe_cad_runtime
from .claim_card import build_claim_cards
from .component_contracts import infer_component_contract
from .database import (
    DATA_DIR,
    DB_PATH,
    PROJECT_ROOT,
    UPLOAD_DIR,
    bootstrap_demo_data_on_startup,
    get_connection,
    init_db,
    seed_if_empty,
)
from .evaluation import metrics_payload, review_summary, run_comparison, run_evaluation
from .graph_reasoning import build_visual_evidence
from .graph_store import get_graph_store
from .ingestion import ingest_directory
from .knowledge_write_pipeline import build_knowledge_write_pipeline
from .model_gateway import (
    agent_route_report,
    generate_text,
    probe_all_models,
    safe_provider_report,
)
from .part_tree_candidates import load_part_tree_candidates
from .retrieval import EQUIPMENT_LABELS, describe_image, retrieve, tokenize
from .resource_registry import load_resource_verification, resource_verification_summary
from .reconstruction_jobs import create_multi_photo_job, create_one_photo_job, get_job
from .sample_expansion import generate_sample_data
from .schemas import (
    CandidateCadFromVisualRequest,
    CandidateCadPromoteRequest,
    CandidateCadReviewRequest,
    CandidateCadSpecPatchRequest,
    CaseCreate,
    FeedbackCreate,
    OnePhotoReconstructionRequest,
    QueryRequest,
    SpatialGuidanceRequest,
)
from .settings import settings
from .spatial_guidance import (
    build_spatial_guidance,
    ensure_standard_3d_models,
    get_standard_model,
    list_standard_models,
)
from .supabase_sync import public_status as supabase_public_status
from .supabase_sync import pull_mutable_data, sync_case, sync_feedback, sync_on_startup_enabled
from .vector_index import rebuild_embeddings
from .visual_analysis import (
    analyze_visual_file,
    list_visual_assets,
    load_visual_asset,
    save_visual_asset,
    visual_query_text,
)
from .workflow import build_tri_mro_alignment, build_workflow_state

FRONTEND_DIR = PROJECT_ROOT / "frontend"


def _feedback_matches(conn, query_text: str, limit: int = 3) -> list[dict]:
    query_terms = set(tokenize(query_text))
    if not query_terms:
        return []
    rows = conn.execute(
        """
        SELECT id, question, corrected_answer, notes, created_at
        FROM feedback
        ORDER BY id DESC
        LIMIT 40
        """
    ).fetchall()
    scored: list[tuple[int, dict]] = []
    for row in rows:
        text = " ".join([row["question"], row["corrected_answer"], row["notes"] or ""])
        score = len(query_terms & set(tokenize(text)))
        if score:
            scored.append((score, dict(row)))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in scored[:limit]]

app = FastAPI(
    title="A1-MAKG：面向设备检修的多模态证据链作业辅助系统",
    description="中国软件杯 A1 赛题原型：以检修证据链为核心，串联多模态检索、作业票、SOP、合规校验、案例沉淀和知识图谱。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_cache_frontend_assets(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static/") or path in {"/marketing", "/promo"}:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/3d-assets", StaticFiles(directory=DATA_DIR / "3d" / "public"), name="three_d_assets")


@app.on_event("startup")
def startup() -> None:
    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        seed_if_empty(conn)
        bootstrap_demo_data_on_startup(conn)
        visual_asset_count = conn.execute("SELECT COUNT(*) AS c FROM visual_assets").fetchone()["c"]
        visual_node_count = conn.execute(
            "SELECT COUNT(*) AS c FROM kg_nodes WHERE type = 'VisualAsset'"
        ).fetchone()["c"]
        if visual_asset_count >= 30 and visual_node_count < 30:
            get_graph_store(conn).rebuild()
        ensure_standard_3d_models(conn)
        if sync_on_startup_enabled():
            pull_mutable_data(conn)
    finally:
        conn.close()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/marketing")
def marketing_homepage() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "marketing.html")


@app.get("/promo")
def promo_homepage() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "marketing.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "db": str(DB_PATH),
        "mode": settings.active_provider,
        "supabase": supabase_public_status(),
        "time": datetime.utcnow().isoformat(timespec="seconds"),
    }


@app.get("/api/providers")
def provider_config() -> dict:
    return {"providers": safe_provider_report()}


@app.get("/api/agent-routing")
def agent_routing() -> dict:
    return {"routes": agent_route_report()}


@app.get("/api/models")
def model_discovery() -> dict:
    return {"results": probe_all_models()}


@app.get("/api/devices")
def devices() -> dict:
    return {
        "devices": [
            {"id": key, "label": value}
            for key, value in EQUIPMENT_LABELS.items()
            if key != "general"
        ],
        "levels": ["一级检修", "二级检修", "三级检修"],
    }


def _finalize_visual_upload(target: Path, safe_name: str) -> dict:
    description = describe_image(safe_name)
    visual_analysis = analyze_visual_file(target, safe_name, description["caption"])
    caption = visual_analysis.get("caption") or description["caption"]
    conn = get_connection(DB_PATH)
    try:
        visual_asset_id = save_visual_asset(
            conn,
            filename=safe_name,
            stored_path=str(target),
            analysis=visual_analysis,
        )
        graph_sync = get_graph_store(conn).rebuild()
    finally:
        conn.close()
    return {
        "filename": safe_name,
        "stored_path": str(target),
        "caption": caption,
        "tags": description["tags"],
        "caption_provider": visual_analysis.get("provider", "local"),
        "caption_model_ok": bool(visual_analysis.get("ok")),
        "visual_asset_id": visual_asset_id,
        "visual_analysis": visual_analysis,
        "graph_sync": graph_sync,
    }


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)) -> dict:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "fault-image").name
    target = UPLOAD_DIR / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}-{safe_name}"
    with target.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    return _finalize_visual_upload(target, safe_name)


@app.post("/api/admin/ingest-manuals")
def ingest_manuals(rebuild: bool = True) -> dict:
    conn = get_connection(DB_PATH)
    try:
        return ingest_directory(conn, rebuild=rebuild)
    finally:
        conn.close()


@app.post("/api/admin/rebuild-index")
def rebuild_index() -> dict:
    conn = get_connection(DB_PATH)
    try:
        return rebuild_embeddings(conn)
    finally:
        conn.close()


@app.post("/api/admin/generate-sample-data")
def generate_samples(case_count: int = 120, eval_count: int = 100) -> dict:
    conn = get_connection(DB_PATH)
    try:
        return generate_sample_data(conn, case_count=case_count, eval_count=eval_count)
    finally:
        conn.close()


@app.post("/api/admin/sync-supabase")
def sync_supabase() -> dict:
    conn = get_connection(DB_PATH)
    try:
        return pull_mutable_data(conn)
    finally:
        conn.close()


@app.post("/api/query")
def query(request: QueryRequest) -> dict:
    conn = get_connection(DB_PATH)
    try:
        visual_asset = load_visual_asset(conn, request.visual_asset_id)
        if request.visual_asset_id and not visual_asset:
            raise HTTPException(status_code=404, detail="visual asset not found")
        visual_context = visual_query_text(visual_asset)
        retrieval_image_context = " ".join(
            part for part in [request.image_caption, visual_context] if part
        )
        manual_hits, case_hits = retrieve(
            conn,
            query=request.text,
            equipment=request.equipment,
            model=request.model,
            image_caption=retrieval_image_context,
            top_k=request.top_k,
        )
        feedback_hints = _feedback_matches(conn, request.text)
        graph_store = get_graph_store(conn)
        graph_paths = graph_store.query_paths(
            request.equipment,
            manual_hits,
            case_hits,
            visual_asset=visual_asset,
        )
        graph_status = graph_store.status()
        resource_summary = resource_verification_summary()
    finally:
        conn.close()

    sop = build_sop(
        request.text,
        request.equipment,
        request.maintenance_level,
        manual_hits,
        case_hits,
    )
    conn = get_connection(DB_PATH)
    try:
        spatial_guidance = build_spatial_guidance(
            conn,
            equipment=request.equipment,
            model_code=request.model,
            text=request.text,
            visual_asset=visual_asset,
            sop=sop,
            manual_hits=manual_hits,
            case_hits=case_hits,
        )
    finally:
        conn.close()
    citations = [
        {
            "type": hit.source_type,
            "title": hit.title,
            "section": hit.section,
            "source": hit.source,
            "source_url": hit.source_url,
            "license": hit.license,
            "page": hit.page,
            "equipment": hit.equipment,
            "model": hit.model,
            "fault_type": hit.fault_type,
            "content": hit.content,
            "confidence": hit.confidence,
            "modality": hit.modality,
            "image_caption": hit.image_caption,
        }
        for hit in manual_hits
    ]
    cases = [
        {
            "title": hit.title,
            "symptoms": hit.section,
            "summary": hit.content,
            "confidence": hit.confidence,
        }
        for hit in case_hits
    ]
    confidence = round(
        sum(hit.confidence for hit in manual_hits + case_hits)
        / max(1, len(manual_hits) + len(case_hits)),
        2,
    )
    system_prompt, user_prompt, fallback_review = build_model_review_prompt(
        request.text, sop, manual_hits, case_hits
    )
    if feedback_hints:
        correction_context = "\n".join(
            f"- 原问题：{item['question']}；修正意见：{item['corrected_answer']}"
            for item in feedback_hints
        )
        user_prompt = f"{user_prompt}\n\n人工修正记录参考：\n{correction_context}"
    model_review = generate_text(system_prompt, user_prompt, fallback_review, role="compliance")
    workflow_state = build_workflow_state(
        text=request.text,
        equipment=request.equipment,
        model=request.model,
        visual_asset=visual_asset,
        image_caption=request.image_caption,
        citations=citations,
        cases=cases,
        graph_paths=graph_paths,
        sop=sop,
        spatial_guidance=spatial_guidance,
        resource_summary=resource_summary,
    )
    spatial_guidance["component_groundings"] = workflow_state["component_groundings"]
    tri_mro_alignment = build_tri_mro_alignment(
        text=request.text,
        equipment=request.equipment,
        model=request.model,
        visual_asset=visual_asset,
        image_caption=request.image_caption,
        citations=citations,
        cases=cases,
        graph_paths=graph_paths,
        sop=sop,
        spatial_guidance=spatial_guidance,
        workflow_state=workflow_state,
    )
    claim_cards = build_claim_cards(
        text=request.text,
        equipment=request.equipment,
        model=request.model,
        visual_asset=visual_asset,
        image_caption=request.image_caption,
        citations=citations,
        cases=cases,
        graph_paths=graph_paths,
        sop=sop,
        spatial_guidance=spatial_guidance,
        workflow_state=workflow_state,
        tri_mro_alignment=tri_mro_alignment,
    )
    primary_claim_card = claim_cards[0]
    tri_mro_alignment["claim_card_id"] = primary_claim_card["claim_id"]
    return {
        "query": request.model + " " + request.text,
        "confidence": confidence,
        "diagnosis": sop["diagnosis"],
        "possible_causes": sop["possible_causes"],
        "sop_steps": sop["sop_steps"],
        "tools_and_parts": sop["tools_and_parts"],
        "acceptance": sop["acceptance"],
        "risk_level": sop["risk_level"],
        "human_review_required": sop["human_review_required"],
        "compliance": sop["compliance"],
        "model_review": {
            "provider": model_review["provider"],
            "model": model_review.get("model", ""),
            "ok": model_review["ok"],
            "text": model_review["text"],
            "error": model_review.get("error", ""),
        },
        "citations": citations,
        "similar_cases": cases,
        "feedback_hints": feedback_hints,
        "visual_analysis": visual_asset.get("analysis") if visual_asset else None,
        "graph_backend": graph_status["backend"],
        "graph_status": graph_status,
        "graph_paths": graph_paths,
        "visual_evidence": build_visual_evidence(
            manual_hits,
            request.image_caption,
            visual_asset=visual_asset,
        ),
        "spatial_guidance": spatial_guidance,
        "workflow_state": workflow_state,
        "tri_mro_alignment": tri_mro_alignment,
        "claim_cards": claim_cards,
        "primary_claim_card": primary_claim_card,
        "resource_verification_summary": resource_summary,
        "agents": agent_trace(
            bool(request.image_caption or visual_asset),
            manual_hits,
            case_hits,
            sop=sop,
            equipment=request.equipment,
            image_caption=retrieval_image_context,
            visual_analysis=visual_asset.get("analysis") if visual_asset else None,
        ),
    }


@app.get("/api/3d/models")
def three_d_models(equipment: str = "") -> dict:
    conn = get_connection(DB_PATH)
    try:
        return {"models": list_standard_models(conn, equipment=equipment)}
    finally:
        conn.close()


@app.get("/api/3d/models/{model_id}")
def three_d_model(model_id: str) -> dict:
    conn = get_connection(DB_PATH)
    try:
        model = get_standard_model(conn, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="3D model not found")
        return model
    finally:
        conn.close()


@app.get("/api/3d/models/{model_id}/files/{file_role}")
def three_d_model_file(model_id: str, file_role: str) -> FileResponse:
    model, target = _resolve_3d_model_file(model_id, file_role)
    media_types = {
        ".json": "application/json",
        ".glb": "model/gltf-binary",
        ".gltf": "model/gltf+json",
        ".step": "model/step",
        ".stp": "model/step",
        ".fcstd": "application/octet-stream",
        ".obj": "text/plain",
        ".stl": "model/stl",
    }
    return FileResponse(
        target,
        media_type=media_types.get(target.suffix.lower(), "application/octet-stream"),
        filename=target.name,
    )


def _resolve_3d_model_file(model_id: str, file_role: str) -> tuple[dict, Path]:
    role_to_field = {
        "source-cad": "source_cad_path",
        "glb": "processed_mesh_path",
        "sidecar": "sidecar_path",
        "conversion-report": "conversion_report",
    }
    field = role_to_field.get(file_role)
    if not field:
        raise HTTPException(status_code=404, detail="3D model file role not found")

    conn = get_connection(DB_PATH)
    try:
        model = get_standard_model(conn, model_id)
    finally:
        conn.close()
    if not model:
        raise HTTPException(status_code=404, detail="3D model not found")

    relative_path = model.get(field) or ""
    if not relative_path:
        raise HTTPException(status_code=404, detail="3D model file role is not available for this model")
    target = (PROJECT_ROOT / relative_path).resolve()
    allowed_roots = [
        (DATA_DIR / "3d" / "authorized_models").resolve(),
        (DATA_DIR / "3d" / "public").resolve(),
        (DATA_DIR / "cad_candidates").resolve(),
    ]
    if not any(target == root or root in target.parents for root in allowed_roots):
        raise HTTPException(status_code=403, detail="3D model file is outside the allowed asset roots")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="3D model file not found")
    return model, target


@app.get("/api/3d/models/{model_id}/files/{file_role}/preview", response_class=HTMLResponse)
def three_d_model_file_preview(model_id: str, file_role: str) -> HTMLResponse:
    model, target = _resolve_3d_model_file(model_id, file_role)
    role_labels = {
        "source-cad": "CAD 原件预览",
        "glb": "GLB 网页模型预览",
        "sidecar": "sidecar 标注预览",
        "conversion-report": "转换报告预览",
    }
    title = role_labels.get(file_role, "3D 文件预览")
    download_url = f"/api/3d/models/{html.escape(model_id)}/files/{html.escape(file_role)}"
    back_url = f"/?tab=spatial&model={html.escape(model_id)}"
    suffix = target.suffix.lower()
    file_size = target.stat().st_size
    preview = ""
    if suffix in {".json", ".step", ".stp", ".obj", ".txt"}:
        text = target.read_text(encoding="utf-8", errors="replace")
        preview = f"<pre>{html.escape(text[:12000])}</pre>"
    elif suffix == ".glb":
        preview = (
            "<div class=\"preview-note\">GLB 是二进制网页模型文件；主 3D 工位会用 Three.js 渲染它。"
            "这里展示文件证据和入口，避免浏览器把二进制内容当下载失败处理。</div>"
        )
    else:
        preview = (
            "<div class=\"preview-note\">该格式浏览器不能稳定直接预览，已保留为授权来源文件。"
            "需要用 FreeCAD、CAD Assistant、Blender 或专业 CAD 工具打开。</div>"
        )
    page = f"""
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(title)} - {html.escape(model.get("title", model_id))}</title>
    <style>
      body {{ margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; background: #eef3f5; color: #102233; }}
      main {{ max-width: 1080px; margin: 0 auto; padding: 28px; }}
      header, section {{ background: #fff; border: 1px solid #d6e0e7; border-radius: 8px; padding: 18px; }}
      header {{ display: grid; gap: 8px; margin-bottom: 14px; }}
      h1 {{ margin: 0; font-size: 24px; }}
      .meta {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
      .meta div {{ border: 1px solid #dce5eb; border-radius: 7px; padding: 10px; background: #f8fbfb; }}
      .meta span {{ display: block; color: #637285; font-size: 12px; }}
      .meta strong {{ overflow-wrap: anywhere; }}
      .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }}
      a {{ color: #075f50; font-weight: 800; }}
      .actions a {{ border: 1px solid #b9d2cb; border-radius: 6px; padding: 8px 10px; background: #eaf6f2; text-decoration: none; }}
      pre {{ margin: 0; max-height: 68vh; overflow: auto; white-space: pre-wrap; word-break: break-word; line-height: 1.45; font-size: 12px; }}
      .preview-note {{ line-height: 1.7; color: #44576a; }}
      @media (max-width: 760px) {{ .meta {{ grid-template-columns: 1fr; }} main {{ padding: 14px; }} }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>{html.escape(title)}</h1>
        <div class="meta">
          <div><span>模型</span><strong>{html.escape(model.get("title", model_id))}</strong></div>
          <div><span>文件名</span><strong>{html.escape(target.name)}</strong></div>
          <div><span>大小</span><strong>{file_size} bytes</strong></div>
        </div>
        <div class="actions">
          <a href="{back_url}">返回 3D 工位</a>
          <a href="{download_url}">下载原始文件</a>
        </div>
      </header>
      <section>{preview}</section>
    </main>
  </body>
</html>
"""
    return HTMLResponse(page)


@app.get("/api/3d/part-tree-candidates")
def three_d_part_tree_candidates(equipment: str = "") -> dict:
    return load_part_tree_candidates(equipment=equipment)


@app.post("/api/3d/guidance")
def three_d_guidance(payload: SpatialGuidanceRequest) -> dict:
    conn = get_connection(DB_PATH)
    try:
        visual_asset = load_visual_asset(conn, payload.visual_asset_id)
        if payload.visual_asset_id and not visual_asset:
            raise HTTPException(status_code=404, detail="visual asset not found")
        guidance = build_spatial_guidance(
            conn,
            equipment=payload.equipment,
            model_code=payload.model,
            text=payload.text,
            visual_asset=visual_asset,
            sop={"sop_steps": payload.sop_steps, "compliance": payload.compliance},
            manual_hits=[],
            case_hits=[],
        )
        model_component_keys = [
            str(item.get("component_key", ""))
            for item in guidance.get("highlighted_components", [])
            if item.get("component_key")
        ]
        contract = infer_component_contract(
            payload.equipment,
            component_keys=[],
            model_component_keys=model_component_keys,
            text=payload.text,
        )
        guidance["component_contract"] = contract
        guidance["binding_precision_level"] = contract["binding_precision_level"]
        guidance["manual_calibration_required"] = contract["manual_calibration_required"]
        return guidance
    finally:
        conn.close()


@app.post("/api/3d/reconstruct/one-photo")
def reconstruct_one_photo(payload: OnePhotoReconstructionRequest) -> dict:
    conn = get_connection(DB_PATH)
    try:
        visual_asset = load_visual_asset(conn, payload.visual_asset_id)
        if not visual_asset:
            raise HTTPException(status_code=404, detail="visual asset not found")
        job = create_one_photo_job(conn, visual_asset, provider=payload.provider or "cached_demo")
        return {"job": job}
    finally:
        conn.close()


@app.post("/api/3d/reconstruct/multi-photo")
async def reconstruct_multi_photo(
    files: list[UploadFile] = File(...),
    equipment: str = "",
    provider: str = "offline_package",
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="at least one image is required")
    conn = get_connection(DB_PATH)
    try:
        job = await create_multi_photo_job(
            conn,
            files=files,
            equipment=equipment,
            provider=provider,
        )
        return {"job": job}
    finally:
        conn.close()


@app.get("/api/3d/jobs/{job_id}")
def three_d_job(job_id: int) -> dict:
    conn = get_connection(DB_PATH)
    try:
        job = get_job(conn, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="3D job not found")
        return {"job": job}
    finally:
        conn.close()


@app.get("/api/cad/candidates")
def cad_candidates(status: str = "", limit: int = 40) -> dict:
    conn = get_connection(DB_PATH)
    try:
        return list_candidate_assets(conn, status=status, limit=limit)
    finally:
        conn.close()


@app.get("/api/cad/runtime")
def cad_runtime() -> dict:
    return probe_cad_runtime()


@app.post("/api/cad/candidates/from-visual")
def cad_candidate_from_visual(payload: CandidateCadFromVisualRequest) -> dict:
    conn = get_connection(DB_PATH)
    try:
        visual_asset = load_visual_asset(conn, payload.visual_asset_id)
        if not visual_asset:
            raise HTTPException(status_code=404, detail="visual asset not found")
        candidate = create_candidate_from_visual_asset(
            conn,
            visual_asset,
            equipment=payload.equipment,
            model=payload.model,
            generator=payload.generator,
        )
        return {"candidate": candidate}
    finally:
        conn.close()


@app.patch("/api/cad/candidates/{candidate_id}/spec")
def cad_candidate_patch_spec(candidate_id: int, payload: CandidateCadSpecPatchRequest) -> dict:
    conn = get_connection(DB_PATH)
    try:
        candidate = patch_candidate_spec(
            conn,
            candidate_id,
            parameters=payload.parameters,
            component_keys=payload.component_keys,
            review_notes=payload.review_notes,
        )
        return {"candidate": candidate}
    finally:
        conn.close()


@app.post("/api/cad/candidates/{candidate_id}/render")
def cad_candidate_render(candidate_id: int) -> dict:
    conn = get_connection(DB_PATH)
    try:
        candidate = regenerate_candidate_artifacts(conn, candidate_id)
        return {"candidate": candidate}
    finally:
        conn.close()


@app.post("/api/cad/candidates/{candidate_id}/review")
def cad_candidate_review(candidate_id: int, payload: CandidateCadReviewRequest) -> dict:
    conn = get_connection(DB_PATH)
    try:
        candidate = review_candidate_asset(
            conn,
            candidate_id,
            status=payload.status,
            reviewer=payload.reviewer,
            notes=payload.notes,
        )
        return {"candidate": candidate}
    finally:
        conn.close()


@app.post("/api/cad/candidates/{candidate_id}/promote")
def cad_candidate_promote(candidate_id: int, payload: CandidateCadPromoteRequest) -> dict:
    conn = get_connection(DB_PATH)
    try:
        candidate = get_candidate_asset(conn, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="candidate CAD asset not found")
        promotion = promote_candidate_to_model(
            conn,
            candidate,
            model_title=payload.model_title,
            component_binding_mode=payload.component_binding_mode,
        )
        save_candidate_promotion(conn, candidate_id, promotion)
        return {"promotion": promotion}
    finally:
        conn.close()


@app.get("/api/cad/candidates/{candidate_id}/files/{file_role}")
def cad_candidate_file(candidate_id: int, file_role: str) -> FileResponse:
    conn = get_connection(DB_PATH)
    try:
        target = resolve_candidate_file(conn, candidate_id, file_role)
    finally:
        conn.close()
    media_types = {
        ".json": "application/json",
        ".py": "text/x-python",
        ".scad": "text/plain",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".step": "model/step",
        ".stp": "model/step",
        ".stl": "model/stl",
        ".glb": "model/gltf-binary",
        ".fcstd": "application/octet-stream",
    }
    return FileResponse(target, media_type=media_types.get(target.suffix.lower(), "application/octet-stream"), filename=target.name)


@app.get("/api/cases")
def list_cases(status: str = "approved") -> dict:
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT * FROM maintenance_cases WHERE status = ? ORDER BY id DESC", (status,)
        ).fetchall()
    finally:
        conn.close()
    return {"cases": [dict(row) for row in rows]}


@app.post("/api/cases")
def create_case(payload: CaseCreate) -> dict:
    conn = get_connection(DB_PATH)
    try:
        cursor = conn.execute(
            """
            INSERT INTO maintenance_cases
            (title, equipment, model, symptoms, fault_type, cause, actions, parts,
             risk_level, status, work_order_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'pending_review', ?)
            """,
            (
                payload.title,
                payload.equipment,
                payload.model,
                payload.symptoms,
                payload.fault_type,
                payload.cause,
                payload.actions,
                payload.parts,
                payload.risk_level,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        sync_result = sync_case(conn, cursor.lastrowid)
        return {"id": cursor.lastrowid, "status": "pending", "supabase_sync": sync_result}
    finally:
        conn.close()


@app.post("/api/cases/{case_id}/approve")
def approve_case(case_id: int) -> dict:
    conn = get_connection(DB_PATH)
    try:
        row = conn.execute("SELECT * FROM maintenance_cases WHERE id = ?", (case_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="case not found")
        approved_at = datetime.utcnow().isoformat(timespec="seconds")
        conn.execute(
            """
            UPDATE maintenance_cases
            SET status = 'approved',
                work_order_status = 'archived_in_graph',
                approved_at = ?
            WHERE id = ?
            """,
            (approved_at, case_id),
        )
        node_id = f"case_{case_id}"
        fault_id = f"fault_{case_id}"
        conn.execute(
            "INSERT OR IGNORE INTO kg_nodes (id, label, type) VALUES (?, ?, ?)",
            (node_id, row["title"], "case"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO kg_nodes (id, label, type) VALUES (?, ?, ?)",
            (fault_id, row["fault_type"], "fault"),
        )
        conn.execute(
            "INSERT INTO kg_edges (source, target, relation) VALUES (?, ?, ?)",
            (node_id, fault_id, "沉淀故障"),
        )
        conn.commit()
        refreshed = conn.execute("SELECT * FROM maintenance_cases WHERE id = ?", (case_id,)).fetchone()
        knowledge_write = build_knowledge_write_pipeline(conn, refreshed, approved=True)
        sync_result = sync_case(conn, case_id)
        return {
            "id": case_id,
            "status": "approved",
            "graph_updated": True,
            "knowledge_write": knowledge_write,
            "supabase_sync": sync_result,
        }
    finally:
        conn.close()


@app.post("/api/feedback")
def create_feedback(payload: FeedbackCreate) -> dict:
    conn = get_connection(DB_PATH)
    try:
        cursor = conn.execute(
            """
            INSERT INTO feedback
            (question, original_answer, corrected_answer, notes, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.question,
                payload.original_answer,
                payload.corrected_answer,
                payload.notes,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        sync_result = sync_feedback(conn, cursor.lastrowid)
        return {"id": cursor.lastrowid, "status": "recorded", "supabase_sync": sync_result}
    finally:
        conn.close()


@app.get("/api/feedback")
def list_feedback(limit: int = 20) -> dict:
    safe_limit = min(max(limit, 1), 100)
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT id, question, original_answer, corrected_answer, notes, created_at
            FROM feedback
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    finally:
        conn.close()
    return {"feedback": [dict(row) for row in rows]}


@app.get("/api/knowledge-graph")
def graph() -> dict:
    conn = get_connection(DB_PATH)
    try:
        nodes = [dict(row) for row in conn.execute("SELECT * FROM kg_nodes").fetchall()]
        edges = [dict(row) for row in conn.execute("SELECT * FROM kg_edges").fetchall()]
    finally:
        conn.close()
    return {"nodes": nodes, "edges": edges}


@app.get("/api/graph/status")
def graph_status() -> dict:
    conn = get_connection(DB_PATH)
    try:
        return get_graph_store(conn).status()
    finally:
        conn.close()


@app.post("/api/admin/graph/rebuild")
def rebuild_graph() -> dict:
    conn = get_connection(DB_PATH)
    try:
        return get_graph_store(conn).rebuild()
    finally:
        conn.close()


@app.get("/api/visual-assets")
def visual_assets(limit: int = 40) -> dict:
    conn = get_connection(DB_PATH)
    try:
        return {"assets": list_visual_assets(conn, limit=limit)}
    finally:
        conn.close()


@app.get("/api/visual-assets/{asset_id}/file")
def visual_asset_file(asset_id: int) -> FileResponse:
    conn = get_connection(DB_PATH)
    try:
        asset = load_visual_asset(conn, asset_id)
    finally:
        conn.close()
    if not asset:
        raise HTTPException(status_code=404, detail="visual asset not found")
    target = Path(asset.get("stored_path") or "").resolve()
    allowed_roots = [
        DATA_DIR.resolve(),
        UPLOAD_DIR.resolve(),
        (PROJECT_ROOT / "materials").resolve(),
      ]
    if not any(target == root or root in target.parents for root in allowed_roots):
        raise HTTPException(status_code=403, detail="visual asset file is outside the allowed asset roots")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="visual asset file not found")
    media_type = asset.get("mime_type") or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(target, media_type=media_type, filename=target.name)


@app.get("/api/metrics")
def metrics() -> dict:
    conn = get_connection(DB_PATH)
    try:
        return metrics_payload(conn)
    finally:
        conn.close()


@app.get("/api/review-status")
def review_status() -> dict:
    conn = get_connection(DB_PATH)
    try:
        return review_summary(conn)
    finally:
        conn.close()


@app.get("/api/image-eval/status")
def image_eval_status() -> dict:
    from scripts.image_eval_status import summarize_manifest

    return summarize_manifest()


@app.get("/api/resources/verification")
def resources_verification() -> dict:
    return load_resource_verification()


@app.post("/api/eval/run")
def run_eval(max_questions: int = 0) -> dict:
    conn = get_connection(DB_PATH)
    try:
        return run_evaluation(conn, max_questions=max_questions)
    finally:
        conn.close()


@app.post("/api/eval/run-comparison")
def run_eval_comparison(max_questions: int = 20) -> dict:
    conn = get_connection(DB_PATH)
    try:
        return run_comparison(conn, max_questions=max_questions)
    finally:
        conn.close()
