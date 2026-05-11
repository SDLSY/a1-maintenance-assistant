from __future__ import annotations

import math
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

EQUIPMENT_LABELS = {
    "motor": "电机",
    "pump": "离心泵",
    "bearing": "轴承",
    "general": "通用规范",
}

SYNONYMS = {
    "异响": ["噪声", "冲击声", "尖锐", "颗粒感"],
    "发热": ["温升", "过热", "端盖温度"],
    "泄漏": ["滴漏", "积液", "水痕", "油污"],
    "振动": ["抖动", "同轴度", "冲击"],
    "检修": ["维修", "拆检", "更换", "复测"],
    "图片": ["图像", "照片", "视觉"],
}


@dataclass
class RetrievalHit:
    source_type: str
    id: int
    score: float
    title: str
    equipment: str
    model: str
    section: str
    content: str
    source: str
    page: int | None
    fault_type: str
    component: str
    confidence: float
    source_url: str = ""
    license: str = ""


def base_tokenize(text: str) -> list[str]:
    normalized = text.lower()
    latin = re.findall(r"[a-z0-9]+", normalized)
    cjk = re.findall(r"[\u4e00-\u9fff]", normalized)
    cjk_bigrams = [a + b for a, b in zip(cjk, cjk[1:])]
    return latin + cjk + cjk_bigrams


def tokenize(text: str) -> list[str]:
    tokens = base_tokenize(text)
    expanded = list(tokens)
    for key, values in SYNONYMS.items():
        if key in text or any(value in text for value in values):
            expanded.extend(base_tokenize(" ".join([key, *values]))[:10])
    return expanded


def _row_text(row: sqlite3.Row, fields: Iterable[str]) -> str:
    return " ".join(str(row[field] or "") for field in fields)


def _score(query_tokens: list[str], text: str, corpus_size: int) -> float:
    if not query_tokens:
        return 0.0
    tf = Counter(tokenize(text))
    if not tf:
        return 0.0
    q = Counter(query_tokens)
    overlap = 0.0
    for token, weight in q.items():
        if token in tf:
            overlap += (1 + math.log(tf[token] + 1)) * weight
    length_norm = 1 + math.log(len(tf) + 1)
    return overlap / length_norm * math.log(corpus_size + 2)


def describe_image(filename: str, hint: str = "") -> dict:
    text = f"{filename} {hint}".lower()
    tags: list[str]
    if any(word in text for word in ["bearing", "轴承", "spall", "剥落"]):
        tags = ["轴承", "剥落", "金属屑", "润滑不足"]
        caption = "图片疑似显示轴承滚道剥落、磨损或润滑脂异常，需要检查游隙、润滑和安装偏斜。"
    elif any(word in text for word in ["pump", "leak", "泵", "泄漏"]):
        tags = ["离心泵", "泄漏", "机械密封", "油污"]
        caption = "图片疑似显示泵体或机械密封区域泄漏，存在液滴、水痕或油污。"
    elif any(word in text for word in ["motor", "电机", "heat", "hot"]):
        tags = ["电机", "过热", "端盖", "轴承"]
        caption = "图片疑似显示电机端盖或轴承区域异常，可能与过热、油污或通风不良相关。"
    else:
        tags = ["设备异常", "磨损", "泄漏", "过热"]
        caption = "图片已接收。未接入云端视觉模型时，系统按设备异常通用标签参与检索。"
    return {"caption": caption, "tags": tags}


def retrieve(
    conn: sqlite3.Connection,
    query: str,
    equipment: str = "",
    model: str = "",
    image_caption: str = "",
    top_k: int = 6,
    use_vectors: bool = True,
) -> tuple[list[RetrievalHit], list[RetrievalHit]]:
    full_query = " ".join([query, model, image_caption]).strip()
    query_tokens = tokenize(full_query)

    from .vector_index import rebuild_embeddings, vector_score_map

    vector_scores: dict[tuple[str, int], float] = {}
    if use_vectors:
        embedding_count = conn.execute("SELECT COUNT(*) AS c FROM chunk_embeddings").fetchone()["c"]
        if not embedding_count:
            rebuild_embeddings(conn)
        vector_scores = vector_score_map(conn, full_query)

    manual_rows = conn.execute("SELECT * FROM manual_chunks").fetchall()
    case_rows = conn.execute(
        "SELECT * FROM maintenance_cases WHERE status = 'approved'"
    ).fetchall()

    manual_hits: list[RetrievalHit] = []
    for row in manual_rows:
        if equipment and row["equipment"] not in {equipment, "general"}:
            continue
        text = _row_text(
            row,
            [
                "title",
                "equipment",
                "model",
                "section",
                "component",
                "fault_type",
                "content",
                "image_caption",
            ],
        )
        score = _score(query_tokens, text, len(manual_rows))
        score += max(0.0, vector_scores.get(("manual", row["id"]), 0.0)) * 3.0
        if row["source_url"]:
            score += 0.75
        if equipment and row["equipment"] in {equipment, "general"}:
            score += 1.4
        if model and model.lower() in str(row["model"]).lower():
            score += 1.2
        if image_caption and row["modality"] == "image":
            score += 0.8
        if score > 0:
            manual_hits.append(
                RetrievalHit(
                    source_type="manual",
                    id=row["id"],
                    score=score,
                    title=row["title"],
                    equipment=row["equipment"],
                    model=row["model"],
                    section=row["section"],
                    content=row["content"],
                    source=row["source"],
                    source_url=row["source_url"],
                    license=row["license"],
                    page=row["page"],
                    fault_type=row["fault_type"],
                    component=row["component"],
                    confidence=0.0,
                )
            )

    case_hits: list[RetrievalHit] = []
    for row in case_rows:
        text = _row_text(
            row,
            [
                "title",
                "equipment",
                "model",
                "symptoms",
                "fault_type",
                "cause",
                "actions",
                "parts",
            ],
        )
        score = _score(query_tokens, text, len(case_rows))
        score += max(0.0, vector_scores.get(("case", row["id"]), 0.0)) * 2.4
        if equipment and row["equipment"] == equipment:
            score += 1.0
        if model and model.lower() in str(row["model"]).lower():
            score += 0.9
        if score > 0:
            case_hits.append(
                RetrievalHit(
                    source_type="case",
                    id=row["id"],
                    score=score,
                    title=row["title"],
                    equipment=row["equipment"],
                    model=row["model"],
                    section=row["symptoms"],
                    content=f"原因：{row['cause']}。处置：{row['actions']}。备件：{row['parts']}。",
                    source="已审核检修案例库",
                    source_url="",
                    license="team-reviewed",
                    page=None,
                    fault_type=row["fault_type"],
                    component="案例",
                    confidence=0.0,
                )
            )

    manual_hits = sorted(manual_hits, key=lambda hit: hit.score, reverse=True)
    case_hits = sorted(case_hits, key=lambda hit: hit.score, reverse=True)
    manual_k = max(3, math.ceil(top_k * 0.65))
    case_k = max(1, top_k - manual_k)
    selected_manual = manual_hits[:manual_k]
    if selected_manual and not any(hit.source_url for hit in selected_manual):
        traced = next((hit for hit in manual_hits[manual_k:] if hit.source_url), None)
        if traced:
            selected_manual[-1] = traced
    selected = selected_manual + case_hits[:case_k]
    combined = sorted(selected, key=lambda hit: hit.score, reverse=True)
    if combined:
        max_score = combined[0].score or 1.0
        for hit in combined:
            hit.confidence = round(min(0.98, max(0.25, hit.score / max_score)), 2)
    return [hit for hit in combined if hit.source_type == "manual"], [
        hit for hit in combined if hit.source_type == "case"
    ]
