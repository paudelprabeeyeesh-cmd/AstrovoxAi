"""FastAPI integration for the math engine.

Mounted under /v1/math. Preserves existing auth/moderation patterns.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Any

from app.utils.auth.auth_utils import get_user_id_from_token
from math_engine.service import compute, list_topics

router = APIRouter(prefix="/v1/math", tags=["math"])


class ComputeRequest(BaseModel):
    topic_id: str
    operation_id: str
    inputs: dict[str, Any] = {}


class ComputeResponse(BaseModel):
    ok: bool
    data: dict[str, Any]


@router.post("/compute", response_model=ComputeResponse)
async def math_compute(request: ComputeRequest, authorization: str = Header(None)):
    user_id = get_user_id_from_token(authorization)
    try:
        result = compute(request.topic_id, request.operation_id, **request.inputs)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc))
    return ComputeResponse(ok=result.get("error") is None, data=result)


@router.get("/topics")
async def math_topics():
    return list_topics()
