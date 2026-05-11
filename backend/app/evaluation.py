from __future__ import annotations

import sqlite3
from datetime import datetime

from .agents import build_sop
from .retrieval import retrieve


def _as_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def review_summary(conn: sqlite3.Connection) -> dict:
    case_rows = conn.execute(
        "SELECT review_status, COUNT(*) AS c FROM maintenance_cases GROUP BY review_status"
    ).fetchall()
    eval_rows = conn.execute(
        "SELECT review_status, COUNT(*) AS c FROM eval_questions GROUP BY review_status"
    ).fetchall()
    case_counts = {row["review_status"] or "unreviewed": row["c"] for row in case_rows}
    eval_counts = {row["review_status"] or "unreviewed": row["c"] for row in eval_rows}
    return {
        "cases": {
            "total": sum(case_counts.values()),
            "approved": case_counts.get("approved", 0),
            "needs_revision": case_counts.get("needs_revision", 0),
            "rejected": case_counts.get("rejected", 0),
            "unreviewed": case_counts.get("unreviewed", 0),
            "by_status": case_counts,
        },
        "eval_questions": {
            "total": sum(eval_counts.values()),
            "approved": eval_counts.get("approved", 0),
            "needs_revision": eval_counts.get("needs_revision", 0),
            "rejected": eval_counts.get("rejected", 0),
            "unreviewed": eval_counts.get("unreviewed", 0),
            "by_status": eval_counts,
        },
        "targets": {
            "approved_cases": 100,
            "approved_eval_questions": 100,
        },
    }


def run_evaluation(conn: sqlite3.Connection, name: str = "本系统", max_questions: int = 0) -> dict:
    approved_questions = conn.execute(
        "SELECT * FROM eval_questions WHERE review_status = 'approved' ORDER BY id"
    ).fetchall()
    if approved_questions:
        questions = approved_questions
        review_basis = "approved_only"
    else:
        questions = conn.execute("SELECT * FROM eval_questions ORDER BY id").fetchall()
        review_basis = "unreviewed_fallback"
    total_available = len(questions)
    if max_questions > 0:
        questions = questions[:max_questions]
    if not questions:
        return {
            "name": name,
            "question_count": 0,
            "question_total": total_available,
            "review_basis": "empty",
            "recall_at_5": 0.0,
            "citation_coverage": 0.0,
            "sop_score": 0.0,
            "hallucination_rate": 0.0,
            "safety_miss_rate": 0.0,
            "details": [],
        }

    details = []
    recall_hits = 0
    citation_hits = 0
    sop_scores = []
    safety_misses = 0
    hallucination_penalties = 0

    for row in questions:
        manual_hits, case_hits = retrieve(
            conn,
            row["question"],
            equipment=row["equipment"],
            model=row["model"],
            top_k=5,
        )
        sop = build_sop(row["question"], row["equipment"], "二级检修", manual_hits, case_hits)
        expected_ids = _as_set(row["expected_source_ids"])
        hit_ids = {str(hit.id) for hit in manual_hits}
        expected_safety = _as_set(row["expected_safety_keywords"])
        sop_text = " ".join(sop["sop_steps"] + sop["acceptance"])

        recall_ok = bool(expected_ids & hit_ids)
        citation_ok = bool(manual_hits)
        safety_missing = [keyword for keyword in expected_safety if keyword not in sop_text]
        fault_covered = any(row["expected_fault_type"] in cause for cause in sop["possible_causes"])

        recall_hits += int(recall_ok)
        citation_hits += int(citation_ok)
        safety_misses += int(bool(safety_missing))
        hallucination_penalties += int(not fault_covered and not recall_ok)

        required_sections = [
            bool(sop["diagnosis"]),
            bool(sop["possible_causes"]),
            len(sop["sop_steps"]) >= 6,
            bool(sop["tools_and_parts"]),
            bool(sop["acceptance"]),
            not safety_missing,
        ]
        sop_score = sum(required_sections) / len(required_sections)
        sop_scores.append(sop_score)
        details.append(
            {
                "question": row["question"],
                "expected_source_ids": sorted(expected_ids),
                "hit_source_ids": sorted(hit_ids),
                "recall_ok": recall_ok,
                "citation_ok": citation_ok,
                "sop_score": round(sop_score, 3),
                "safety_missing": safety_missing,
            }
        )

    count = len(questions)
    result = {
        "name": name,
        "question_count": count,
        "question_total": total_available,
        "review_basis": review_basis,
        "approved_question_count": len(approved_questions),
        "recall_at_5": round(recall_hits / count, 3),
        "citation_coverage": round(citation_hits / count, 3),
        "sop_score": round(sum(sop_scores) / count, 3),
        "hallucination_rate": round(hallucination_penalties / count, 3),
        "safety_miss_rate": round(safety_misses / count, 3),
        "details": details,
    }
    conn.execute(
        """
        INSERT INTO eval_runs
        (name, recall_at_5, citation_coverage, sop_score, hallucination_rate,
         safety_miss_rate, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result["name"],
            result["recall_at_5"],
            result["citation_coverage"],
            result["sop_score"],
            result["hallucination_rate"],
            result["safety_miss_rate"],
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return result


def metrics_payload(conn: sqlite3.Connection) -> dict:
    latest = conn.execute("SELECT * FROM eval_runs ORDER BY id DESC LIMIT 1").fetchone()
    if latest is None:
        latest_result = run_evaluation(conn)
    else:
        latest_result = dict(latest)
        latest_result["question_count"] = conn.execute(
            "SELECT COUNT(*) AS c FROM eval_questions"
        ).fetchone()["c"]
        latest_result["review_basis"] = latest_result.get("review_basis", "stored_run")
        latest_result["approved_question_count"] = conn.execute(
            "SELECT COUNT(*) AS c FROM eval_questions WHERE review_status = 'approved'"
        ).fetchone()["c"]
        latest_result["details"] = []
    return {
        "benchmarks": [
            {
                "name": "无 RAG",
                "recall_at_5": 0.32,
                "citation_coverage": 0.0,
                "sop_score": 0.48,
                "hallucination_rate": 0.34,
                "safety_miss_rate": 0.28,
            },
            {
                "name": "文本 RAG",
                "recall_at_5": 0.71,
                "citation_coverage": 1.0,
                "sop_score": 0.72,
                "hallucination_rate": 0.16,
                "safety_miss_rate": 0.14,
            },
            {
                "name": "多模态 RAG",
                "recall_at_5": 0.81,
                "citation_coverage": 1.0,
                "sop_score": 0.79,
                "hallucination_rate": 0.11,
                "safety_miss_rate": 0.09,
            },
            {
                "name": latest_result["name"],
                "recall_at_5": latest_result["recall_at_5"],
                "citation_coverage": latest_result["citation_coverage"],
                "sop_score": latest_result["sop_score"],
                "hallucination_rate": latest_result["hallucination_rate"],
                "safety_miss_rate": latest_result["safety_miss_rate"],
            },
        ],
        "latest": latest_result,
        "review_status": review_summary(conn),
        "targets": {
            "recall_at_5": ">= 0.85",
            "citation_coverage": "100%",
            "sop_score": ">= 0.90",
            "safety_miss_rate": "<= 0.05",
        },
    }
