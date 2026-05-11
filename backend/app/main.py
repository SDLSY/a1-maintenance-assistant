from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .agents import agent_trace, build_model_review_prompt, build_sop
from .database import (
    DB_PATH,
    PROJECT_ROOT,
    UPLOAD_DIR,
    bootstrap_demo_data_on_startup,
    get_connection,
    init_db,
    seed_if_empty,
)
from .evaluation import metrics_payload, review_summary, run_comparison, run_evaluation
from .ingestion import ingest_directory
from .model_gateway import (
    agent_route_report,
    caption_image_file,
    generate_text,
    probe_all_models,
    safe_provider_report,
)
from .retrieval import EQUIPMENT_LABELS, describe_image, retrieve, tokenize
from .sample_expansion import generate_sample_data
from .schemas import CaseCreate, FeedbackCreate, QueryRequest
from .settings import settings
from .supabase_sync import public_status as supabase_public_status
from .supabase_sync import pull_mutable_data, sync_case, sync_feedback, sync_on_startup_enabled
from .vector_index import rebuild_embeddings

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
    title="A1 多模态设备检修知识检索与作业辅助系统",
    description="中国软件杯 A1 赛题原型：多模态检索、SOP、合规校验、案例沉淀和知识图谱。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    conn = get_connection(DB_PATH)
    try:
        init_db(conn)
        seed_if_empty(conn)
        bootstrap_demo_data_on_startup(conn)
        if sync_on_startup_enabled():
            pull_mutable_data(conn)
    finally:
        conn.close()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


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


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)) -> dict:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "fault-image").name
    target = UPLOAD_DIR / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{safe_name}"
    with target.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    description = describe_image(safe_name)
    model_caption = caption_image_file(str(target), description["caption"])
    return {
        "filename": safe_name,
        "stored_path": str(target),
        "caption": model_caption["caption"],
        "tags": description["tags"],
        "caption_provider": model_caption["provider"],
        "caption_model_ok": model_caption["ok"],
    }


@app.post("/api/admin/ingest-manuals")
def ingest_manuals() -> dict:
    conn = get_connection(DB_PATH)
    try:
        return ingest_directory(conn)
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
        manual_hits, case_hits = retrieve(
            conn,
            query=request.text,
            equipment=request.equipment,
            model=request.model,
            image_caption=request.image_caption,
            top_k=request.top_k,
        )
        feedback_hints = _feedback_matches(conn, request.text)
    finally:
        conn.close()

    sop = build_sop(
        request.text,
        request.equipment,
        request.maintenance_level,
        manual_hits,
        case_hits,
    )
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
        "agents": agent_trace(
            bool(request.image_caption),
            manual_hits,
            case_hits,
            sop=sop,
            equipment=request.equipment,
            image_caption=request.image_caption,
        ),
    }


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
             risk_level, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
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
        conn.execute("UPDATE maintenance_cases SET status = 'approved' WHERE id = ?", (case_id,))
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
        sync_result = sync_case(conn, case_id)
        return {"id": case_id, "status": "approved", "graph_updated": True, "supabase_sync": sync_result}
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
