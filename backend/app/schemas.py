from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1)
    equipment: str = "motor"
    model: str = ""
    maintenance_level: str = "二级检修"
    image_caption: str = ""
    visual_asset_id: int | None = None
    top_k: int = 6


class SpatialGuidanceRequest(BaseModel):
    text: str = ""
    equipment: str = "motor"
    model: str = ""
    visual_asset_id: int | None = None
    sop_steps: list[str] = Field(default_factory=list)
    compliance: list[dict] = Field(default_factory=list)


class OnePhotoReconstructionRequest(BaseModel):
    visual_asset_id: int
    provider: str = "cached_demo"


class CandidateCadFromVisualRequest(BaseModel):
    visual_asset_id: int
    equipment: str = ""
    model: str = ""
    generator: str = "cadquery_openscad"


class CandidateCadReviewRequest(BaseModel):
    status: str = "needs_review"
    reviewer: str = ""
    notes: str = ""


class CandidateCadSpecPatchRequest(BaseModel):
    parameters: dict = Field(default_factory=dict)
    component_keys: list[str] = Field(default_factory=list)
    review_notes: str = ""


class CandidateCadPromoteRequest(BaseModel):
    model_title: str
    component_binding_mode: str = "candidate_component_key"


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
