from __future__ import annotations

import sys
import os
import csv
import re
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["ACTIVE_MODEL_PROVIDER"] = "local"
os.environ["TEXT_AGENT_PROVIDER"] = "local"
os.environ["VISION_AGENT_PROVIDER"] = "local"
os.environ["EMBEDDING_AGENT_PROVIDER"] = "local"
os.environ["COMPLIANCE_AGENT_PROVIDER"] = "local"
os.environ["KNOWLEDGE_AGENT_PROVIDER"] = "local"
os.environ["A1_DB_PATH"] = str(ROOT / "data" / "test-maintenance.db")

from backend.app.database import reset_demo_db  # noqa: E402
from backend.app.main import app  # noqa: E402


def setup_module() -> None:
    reset_demo_db()


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_favicon_does_not_404() -> None:
    response = client.get("/favicon.ico")
    assert response.status_code in {200, 204}


def test_query_returns_sop_citations_and_compliance() -> None:
    response = client.post(
        "/api/query",
        json={
            "text": "电机端盖温度升高，伴随低频振动和轴承异响",
            "equipment": "motor",
            "model": "Y2-160M",
            "maintenance_level": "二级检修",
            "top_k": 6,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citations"]
    assert body["sop_steps"]
    assert any(item["code"] == "LOTO" for item in body["compliance"])
    assert body["agents"]
    assert body["model_review"]["text"]
    assert body["model_review"]["provider"] in {"local", "openai", "opencode", "codex", "spatialai"}


def test_case_approval_updates_graph() -> None:
    created = client.post(
        "/api/cases",
        json={
            "title": "测试案例：泵机械密封泄漏",
            "equipment": "pump",
            "model": "ISG80-160",
            "symptoms": "密封处有连续滴漏",
            "fault_type": "泄漏",
            "cause": "O 形圈老化",
            "actions": "隔离泄压后更换密封组件",
            "parts": "机械密封组件",
            "risk_level": "high",
        },
    )
    assert created.status_code == 200
    case_id = created.json()["id"]
    approved = client.post(f"/api/cases/{case_id}/approve")
    assert approved.status_code == 200
    graph = client.get("/api/knowledge-graph").json()
    assert any(node["id"] == f"case_{case_id}" for node in graph["nodes"])


def test_feedback_roundtrip_and_query_hints() -> None:
    created = client.post(
        "/api/feedback",
        json={
            "question": "电机轴承温升并伴随低频振动",
            "original_answer": "只建议补充润滑脂。",
            "corrected_answer": "必须先断电挂牌，复测振动频谱，再拆检轴承游隙和润滑污染。",
            "notes": "原答案漏掉 LOTO 和复测。",
        },
    )
    assert created.status_code == 200

    listed = client.get("/api/feedback")
    assert listed.status_code == 200
    body = listed.json()
    assert body["feedback"]
    assert "sk-" not in listed.text.lower()

    query = client.post(
        "/api/query",
        json={
            "text": "电机轴承温升，低频振动明显",
            "equipment": "motor",
            "model": "Y2-160M",
            "maintenance_level": "二级检修",
            "top_k": 6,
        },
    )
    assert query.status_code == 200
    assert query.json()["feedback_hints"]


def test_provider_report_redacts_keys() -> None:
    response = client.get("/api/providers")
    assert response.status_code == 200
    text = response.text.lower()
    assert "sk-" not in text

    routing = client.get("/api/agent-routing")
    assert routing.status_code == 200
    routes = routing.json()["routes"]
    assert {route["role"] for route in routes} >= {"text", "vision", "embedding", "compliance", "knowledge"}
    assert "sk-" not in routing.text.lower()


def test_public_source_manifest_covers_target_equipment() -> None:
    import json

    manifest = ROOT / "data" / "sources" / "public_manual_sources.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    sources = [source for source in payload["sources"] if source.get("active", True)]
    assert len(sources) >= 8
    assert {source["equipment"] for source in sources} >= {"motor", "pump", "bearing"}
    for source in sources:
        assert source["id"]
        assert source["source_url"].startswith("https://")
        assert source["target_filename"].endswith(".pdf")
        assert "redistribution not assumed" in source["license"]


def test_review_pack_export_has_required_columns(tmp_path) -> None:
    from scripts.export_review_pack import export_review_pack

    output_dir = tmp_path / "review"
    result = export_review_pack(review_dir=output_dir)
    assert result["cases"] >= 1
    assert result["eval_questions"] >= 1
    cases_csv = output_dir / "mechanical_cases_review.csv"
    eval_csv = output_dir / "eval_questions_review.csv"
    assert cases_csv.exists()
    assert eval_csv.exists()

    with cases_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        case_fields = set(next(csv.DictReader(handle)).keys())
    with eval_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        eval_fields = set(next(csv.DictReader(handle)).keys())

    assert {"review_status", "reviewer", "review_notes", "decision"} <= case_fields
    assert {"mechanical_accuracy_score", "sop_completeness_score", "safety_score"} <= case_fields
    assert {"review_status", "reviewer", "review_notes", "expected_reference_ok"} <= eval_fields


def test_rebuild_index_and_eval_metrics() -> None:
    rebuilt = client.post("/api/admin/rebuild-index")
    assert rebuilt.status_code == 200
    assert rebuilt.json()["manual"] >= 10

    evaluation = client.post("/api/eval/run?max_questions=4")
    assert evaluation.status_code == 200
    body = evaluation.json()
    assert body["question_count"] >= 4
    assert body["question_count"] <= body["question_total"]
    assert body["citation_coverage"] == 1.0
    assert body["review_basis"] in {"approved_only", "unreviewed_fallback"}

    metrics = client.get("/api/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["latest"]["question_count"] >= 4
    assert "review_status" in metrics.json()

    review = client.get("/api/review-status")
    assert review.status_code == 200
    assert review.json()["targets"]["approved_cases"] == 100


def test_submission_package_excludes_secrets_and_runtime_assets(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package

    archive = build_submission_package(output_dir=tmp_path, timestamp="20260510-0000")
    assert archive.exists()

    with zipfile.ZipFile(archive) as package:
        names = set(package.namelist())

        assert "README.md" in names
        assert ".env.example" in names
        assert "backend/app/main.py" in names
        assert "config/model_profiles.json" in names
        assert "frontend/index.html" in names
        assert "docs/DATA_SOURCES.md" in names
        assert "docs/DEPLOYMENT_LOONGARCH.md" in names
        assert "docs/DEPLOYMENT_PUBLIC.md" in names
        assert "docs/SUPABASE_SCHEMA.sql" in names
        assert "data/sources/public_manual_sources.json" in names
        assert "data/review/mechanical_cases_review.csv" in names
        assert "data/review/eval_questions_review.csv" in names
        assert "render.yaml" in names
        assert "runtime.txt" in names
        assert "SUBMISSION_MANIFEST.md" in names

        forbidden = (
            ".env",
            ".env.local",
            "data/maintenance.db",
            "data/test-maintenance.db",
        )
        assert not any(name in forbidden for name in names)
        assert not any(name.endswith(".pdf") for name in names)
        assert not any(".venv/" in name or "__pycache__/" in name or ".pytest_cache/" in name for name in names)

        text_suffixes = (".py", ".md", ".html", ".js", ".css", ".json", ".txt", ".ps1", ".csv", ".sql", ".yaml", ".example")
        for name in names:
            if name.endswith(text_suffixes):
                text = package.read(name).decode("utf-8", errors="ignore").lower()
                assert not re.search(r"sk-[a-z0-9_-]{12,}", text)


def test_readiness_audit_reports_real_evidence_and_external_gaps(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package
    from scripts.audit_readiness import run_audit, write_markdown_report

    archive = build_submission_package(output_dir=tmp_path, timestamp="20260510-audit")
    result = run_audit(submission_archive=archive)

    assert result["ready"] is False
    assert result["summary"]["manual_chunks"] >= 10
    assert result["summary"]["review_case_rows"] >= 1
    assert result["summary"]["review_eval_rows"] >= 1
    assert result["summary"]["submission_forbidden_entries"] == 0
    assert result["checks"]["web_system"]["status"] == "pass"
    assert result["checks"]["submission_package"]["status"] == "pass"
    assert result["checks"]["mechanical_review"]["status"] == "blocked"
    assert result["checks"]["loongarch_runtime"]["status"] == "blocked"
    assert any("LoongArch" in item for item in result["missing_resources"])

    report = write_markdown_report(result, output_path=tmp_path / "READINESS.md")
    text = report.read_text(encoding="utf-8")
    assert "A1 Readiness Audit" in text
    assert "mechanical_review" in text
    assert "loongarch_runtime" in text


def test_readiness_audit_public_mode_does_not_block_on_loongarch(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package
    from scripts.audit_readiness import run_audit

    archive = build_submission_package(output_dir=tmp_path, timestamp="20260510-public")
    result = run_audit(submission_archive=archive, deployment_mode="public")

    assert result["deployment_mode"] == "public"
    assert result["checks"]["loongarch_runtime"]["required"] is False
    assert result["checks"]["public_demo_deployment"]["status"] == "pass"
    assert not any("LoongArch" in item for item in result["missing_resources"])


def test_review_progress_summarizes_review_csvs(tmp_path) -> None:
    from scripts.review_progress import summarize_review_dir, write_markdown_report

    review_dir = tmp_path / "review"
    review_dir.mkdir()
    cases_csv = review_dir / "mechanical_cases_review.csv"
    eval_csv = review_dir / "eval_questions_review.csv"
    cases_csv.write_text(
        "\n".join(
            [
                "id,review_status,decision,reviewer,review_notes",
                "1,approved,approve,teacher,ok",
                "2,approved,approve,teacher,ok",
                "3,needs_revision,revise,teacher,add safety item",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    eval_csv.write_text(
        "\n".join(
            [
                "id,review_status,decision,reviewer,review_notes",
                "1,approved,approve,teacher,ok",
                "2,approved,approve,teacher,ok",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = summarize_review_dir(review_dir, required_cases=2, required_eval_questions=2)
    assert result["ready_for_import"] is True
    assert result["ready_for_goal"] is True
    assert result["cases"]["approved"] == 2
    assert result["cases"]["needs_revision"] == 1
    assert result["eval_questions"]["approved"] == 2

    report = write_markdown_report(result, tmp_path / "review-status.md")
    text = report.read_text(encoding="utf-8")
    assert "Mechanical Review Progress" in text
    assert "ready_for_goal" in text


def test_build_ppt_creates_deck(tmp_path) -> None:
    from scripts.build_ppt import build_presentation

    output = build_presentation(tmp_path / "deck.pptx")
    assert output.exists()
    with zipfile.ZipFile(output) as package:
        names = package.namelist()
        assert "ppt/presentation.xml" in names
        slide_count = sum(1 for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        assert slide_count >= 10


def test_build_docx_creates_work_description(tmp_path) -> None:
    from docx import Document
    from scripts.build_docx import build_work_description_docx

    output = build_work_description_docx(output_path=tmp_path / "work-description.docx")
    assert output.exists()
    doc = Document(output)
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    assert "作品说明书" in text
    assert "赛题要求对应" in text
    assert "创新点" in text


def test_loongarch_acceptance_report_marks_current_machine_not_validated(tmp_path) -> None:
    from scripts.loongarch_acceptance import collect_acceptance, write_markdown_report

    result = collect_acceptance(api_base_url="")
    assert result["loongarch_validated"] is False
    assert result["checks"]["platform"]["status"] in {"blocked", "pass"}
    assert "machine" in result["platform"]

    report = write_markdown_report(result, tmp_path / "loongarch-acceptance.md")
    text = report.read_text(encoding="utf-8")
    assert "LoongArch Acceptance Report" in text
    assert "loongarch_validated" in text


def test_final_validation_collects_blockers(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package
    from scripts.final_validation import collect_final_validation, write_markdown_report

    archive = build_submission_package(output_dir=tmp_path, timestamp="final-validation")
    result = collect_final_validation(submission_archive=archive, api_base_url="")
    assert result["ready"] is False
    assert "mechanical_review" in result["blockers"]
    assert "loongarch_runtime" in result["blockers"]
    assert result["submission"]["submission_forbidden_entries"] == 0

    report = write_markdown_report(result, tmp_path / "final-validation.md")
    text = report.read_text(encoding="utf-8")
    assert "Final Validation Report" in text
    assert "mechanical_review" in text


def test_final_validation_public_mode_skips_loongarch_blockers(tmp_path) -> None:
    from scripts.build_submission_package import build_submission_package
    from scripts.final_validation import collect_final_validation

    archive = build_submission_package(output_dir=tmp_path, timestamp="final-validation-public")
    result = collect_final_validation(
        submission_archive=archive,
        api_base_url="",
        deployment_mode="public",
    )

    assert result["deployment_mode"] == "public"
    assert "loongarch_runtime" not in result["blockers"]
    assert "loongarch_acceptance" not in result["blockers"]
    assert result["readiness"]["checks"]["public_demo_deployment"] == "pass"
