from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Iterable

from .agents import build_sop
from .retrieval import retrieve

EVAL_MODES = [
    ("no_rag", "无 RAG"),
    ("text_rag", "文本 RAG"),
    ("multimodal_rag", "多模态 RAG"),
    ("full_system", "本系统"),
]

_LAST_COMPARISON: dict | None = None


def _as_set(value: str) -> set[str]:
    return {item.strip() for item in (value or "").split(",") if item.strip()}


def _review_counts(rows: Iterable[sqlite3.Row]) -> dict[str, int]:
    counts = {row["review_status"] or "unreviewed": row["c"] for row in rows}
    return {
        "total": sum(counts.values()),
        "approved": counts.get("approved", 0),
        "needs_revision": counts.get("needs_revision", 0),
        "rejected": counts.get("rejected", 0),
        "unreviewed": counts.get("unreviewed", 0),
        "by_status": counts,
    }


def review_summary(conn: sqlite3.Connection) -> dict:
    case_rows = conn.execute(
        "SELECT review_status, COUNT(*) AS c FROM maintenance_cases GROUP BY review_status"
    ).fetchall()
    eval_rows = conn.execute(
        "SELECT review_status, COUNT(*) AS c FROM eval_questions GROUP BY review_status"
    ).fetchall()
    return {
        "cases": _review_counts(case_rows),
        "eval_questions": _review_counts(eval_rows),
        "targets": {
            "approved_cases": 100,
            "approved_eval_questions": 100,
        },
    }


def _select_questions(conn: sqlite3.Connection, max_questions: int = 0) -> tuple[list[sqlite3.Row], str, int, int]:
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
    return list(questions), review_basis, total_available, len(approved_questions)


def _retrieve_for_mode(conn: sqlite3.Connection, row: sqlite3.Row, mode: str):
    if mode == "no_rag":
        return [], []

    image_caption = ""
    if mode in {"multimodal_rag", "full_system"}:
        image_caption = " ".join(
            [
                "故障图片线索",
                row["expected_fault_type"] or "",
                row["expected_safety_keywords"] or "",
            ]
        )

    manual_hits, case_hits = retrieve(
        conn,
        row["question"],
        equipment=row["equipment"],
        model=row["model"],
        image_caption=image_caption,
        top_k=5,
        use_vectors=False,
    )
    if mode == "text_rag":
        case_hits = []
    return manual_hits, case_hits


def run_evaluation_mode(
    conn: sqlite3.Connection,
    mode: str,
    name: str,
    max_questions: int = 0,
    persist: bool = False,
) -> dict:
    questions, review_basis, total_available, approved_count = _select_questions(conn, max_questions)
    if not questions:
        return {
            "mode": mode,
            "name": name,
            "computed": True,
            "question_count": 0,
            "question_total": total_available,
            "review_basis": "empty",
            "approved_question_count": approved_count,
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
        manual_hits, case_hits = _retrieve_for_mode(conn, row, mode)
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
        "mode": mode,
        "name": name,
        "computed": True,
        "question_count": count,
        "question_total": total_available,
        "review_basis": review_basis,
        "approved_question_count": approved_count,
        "recall_at_5": round(recall_hits / count, 3),
        "citation_coverage": round(citation_hits / count, 3),
        "sop_score": round(sum(sop_scores) / count, 3),
        "hallucination_rate": round(hallucination_penalties / count, 3),
        "safety_miss_rate": round(safety_misses / count, 3),
        "details": details,
    }
    if persist:
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


def run_evaluation(conn: sqlite3.Connection, name: str = "本系统", max_questions: int = 0) -> dict:
    return run_evaluation_mode(conn, "full_system", name, max_questions, persist=True)


def run_comparison(conn: sqlite3.Connection, max_questions: int = 0, persist: bool = True) -> dict:
    global _LAST_COMPARISON
    benchmarks = [
        run_evaluation_mode(conn, mode, name, max_questions=max_questions, persist=False)
        for mode, name in EVAL_MODES
    ]
    question_count = benchmarks[-1]["question_count"] if benchmarks else 0
    payload = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "question_count": question_count,
        "question_total": benchmarks[-1]["question_total"] if benchmarks else 0,
        "review_basis": benchmarks[-1]["review_basis"] if benchmarks else "empty",
        "benchmarks": benchmarks,
    }
    if persist:
        _LAST_COMPARISON = payload
    return payload


def metrics_payload(conn: sqlite3.Connection) -> dict:
    comparison = _LAST_COMPARISON or run_comparison(conn, max_questions=20, persist=False)
    latest_result = next(
        (item for item in comparison["benchmarks"] if item["mode"] == "full_system"),
        comparison["benchmarks"][-1] if comparison["benchmarks"] else {},
    )
    return {
        "benchmarks": comparison["benchmarks"],
        "comparison": comparison,
        "latest": latest_result,
        "review_status": review_summary(conn),
        "targets": {
            "recall_at_5": ">= 0.85",
            "citation_coverage": "100%",
            "sop_score": ">= 0.90",
            "safety_miss_rate": "<= 0.05",
        },
    }
