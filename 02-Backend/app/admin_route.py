"""Cost management and compliance API routes."""

from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field
from typing import Optional

from .cost_management import cost_tracker
from .compliance import compliance_manager
from .ai_evaluation import prompt_manager, quality_scorer, benchmark_suite
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/admin", tags=["admin"])


# Cost Management Routes

@router.get("/costs/usage")
async def get_cost_usage(authorization: str = Header(None), days: int = 30):
    """Get cost usage report."""
    user_id = get_user_id_from_token(authorization)
    report = cost_tracker.get_usage_report(user_id, days)
    return {"status": "OK", **report}


@router.get("/costs/forecast")
async def get_cost_forecast(authorization: str = Header(None), days: int = 30):
    """Get cost forecast."""
    user_id = get_user_id_from_token(authorization)
    forecast = cost_tracker.get_cost_forecast(user_id, days)
    return {"status": "OK", **forecast}


@router.get("/costs/providers")
async def get_provider_costs(authorization: str = Header(None)):
    """Get provider cost comparison."""
    user_id = get_user_id_from_token(authorization)
    comparison = cost_tracker.get_provider_cost_comparison(user_id)
    return {"status": "OK", "providers": comparison}


# Compliance Routes

@router.post("/compliance/export")
async def request_export(authorization: str = Header(None)):
    """Request GDPR data export."""
    user_id = get_user_id_from_token(authorization)
    export = compliance_manager.request_data_export(user_id)
    return {
        "status": "OK",
        "export": {"id": export.id, "status": export.status},
    }


@router.post("/compliance/delete")
async def request_deletion(authorization: str = Header(None)):
    """Request right-to-delete."""
    user_id = get_user_id_from_token(authorization)
    result = compliance_manager.request_data_deletion(user_id)
    return {"status": "OK", **result}


@router.get("/compliance/status")
async def get_compliance_status(authorization: str = Header(None)):
    """Get compliance status."""
    user_id = get_user_id_from_token(authorization)
    return {
        "status": "OK",
        **compliance_manager.get_compliance_status(user_id),
    }


# AI Evaluation Routes

class CreatePromptRequest(BaseModel):
    name: str
    content: str


class ScoreRequest(BaseModel):
    response: str
    expected: str = ""


@router.post("/prompts")
async def create_prompt(request: CreatePromptRequest, authorization: str = Header(None)):
    """Create a prompt version."""
    user_id = get_user_id_from_token(authorization)
    prompt = prompt_manager.create_prompt(request.name, request.content)
    return {
        "status": "OK",
        "prompt": {
            "id": prompt.id,
            "name": prompt.name,
            "version": prompt.version,
        },
    }


@router.get("/prompts/{name}")
async def get_prompt(name: str, authorization: str = Header(None)):
    """Get active prompt."""
    user_id = get_user_id_from_token(authorization)
    prompt = prompt_manager.get_active_prompt(name)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return {
        "status": "OK",
        "prompt": {
            "id": prompt.id,
            "name": prompt.name,
            "content": prompt.content,
            "version": prompt.version,
        },
    }


@router.post("/evaluate/score")
async def score_response(request: ScoreRequest, authorization: str = Header(None)):
    """Score an AI response."""
    user_id = get_user_id_from_token(authorization)
    result = quality_scorer.score_response(request.response, request.expected)
    return {"status": "OK", **result}


@router.get("/benchmarks")
async def get_benchmarks(authorization: str = Header(None)):
    """Get benchmark results."""
    user_id = get_user_id_from_token(authorization)
    report = benchmark_suite.get_benchmark_report()
    return {"status": "OK", **report}
