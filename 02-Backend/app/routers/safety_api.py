"""
Safety API.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..core.safety import SafetyAPI

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/safety", tags=["safety"])

safety_api = SafetyAPI()


class ModerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000)
    user_id: Optional[str] = Field(None, max_length=100)
    interaction_id: Optional[str] = Field(None, max_length=100)


class ModerateResponse(BaseModel):
    safe: bool
    flags: List[str]
    confidence: float
    action: str


class FeedbackRequest(BaseModel):
    user_id: Optional[str] = Field(None, max_length=100)
    interaction_id: str = Field(..., max_length=100)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=5000)


class FeedbackResponse(BaseModel):
    status: str
    average_rating: float


@router.post("/moderate", response_model=ModerateResponse)
async def moderate_text(request: ModerateRequest):
    result = safety_api.moderate(request.text, user_id=request.user_id, interaction_id=request.interaction_id)
    return ModerateResponse(safe=result.safe, flags=result.flags, confidence=result.confidence, action=result.action)


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    safety_api.record_feedback(request.user_id, request.interaction_id, request.rating, request.comment)
    summary = safety_api.get_feedback_summary()
    return FeedbackResponse(status="OK", average_rating=summary.get("average_rating", 0.0))


@router.get("/audit")
async def get_audit_log(limit: int = 100):
    entries = safety_api.get_audit_log(limit=limit)
    return {"status": "OK", "entries": entries}
