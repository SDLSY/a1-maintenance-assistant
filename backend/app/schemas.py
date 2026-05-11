from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1)
    equipment: str = "motor"
    model: str = ""
    maintenance_level: str = "二级检修"
    image_caption: str = ""
    top_k: int = 6


class CaseCreate(BaseModel):
    title: str
    equipment: str
    model: str
    symptoms: str
    fault_type: str
    cause: str
    actions: str
    parts: str = ""
    risk_level: str = "medium"


class FeedbackCreate(BaseModel):
    question: str
    original_answer: str
    corrected_answer: str
    notes: str = ""

