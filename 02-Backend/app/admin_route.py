"""Cost management and compliance API routes.

Security: All endpoints require admin role verification.
"""

from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, Field
from typing import Optional

from .cost_management import cost_tracker
from .compliance import compliance_manager
from .ai_evaluation import prompt_manager, quality_scorer, benchmark_suite
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(authorization: str = Header(None)) -> str:
    """Verify the user has admin role. Returns user_id if authorized."""
    user_id = get_user_id_from_token(authorization)

    # Check admin role from authorization header format: "Bearer <token>:admin"
    # In production, this should check JWT claims or database roles
    if not authorization or ":admin" not in authorization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user_id


# Cost Management Routes

@router.get("/costs/usage")
async def get_cost_usage(
    days: int = 30,
    user_id: str = Depends(require_admin),
):
    """Get cost usage report."""
    report = cost_tracker.get_usage_report(user_id, days)
    return {"status": "OK", **report}


@router.get("/costs/forecast")
async def get_cost_forecast(
    days: int = 30,
    user_id: str = Depends(require_admin),
):
    """Get cost forecast."""
    forecast = cost_tracker.get_cost_forecast(user_id, days)
    return {"status": "OK", **forecast}


@router.get("/costs/providers")
async def get_provider_costs(
    user_id: str = Depends(require_admin),
):
    """Get provider cost comparison."""
    comparison = cost_tracker.get_provider_cost_comparison(user_id)
    return {"status": "OK", "providers": comparison}


# Compliance Routes

@router.post("/compliance/export")
async def request_export(
    user_id: str = Depends(require_admin),
):
    """Request GDPR data export."""
    export = compliance_manager.request_data_export(user_id)
    return {
        "status": "OK",
        "export": {"id": export.id, "status": export.status},
    }


@router.post("/compliance/delete")
async def request_deletion(
    user_id: str = Depends(require_admin),
):
    """Request right-to-delete."""
    result = compliance_manager.request_data_deletion(user_id)
    return {"status": "OK", **result}


@router.get("/compliance/status")
async def get_compliance_status(
    user_id: str = Depends(require_admin),
):
    """Get compliance status."""
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
async def create_prompt(
    request: CreatePromptRequest,
    user_id: str = Depends(require_admin),
):
    """Create a prompt version."""
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
async def get_prompt(
    name: str,
    user_id: str = Depends(require_admin),
):
    """Get active prompt."""
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
async def score_response(
    request: ScoreRequest,
    user_id: str = Depends(require_admin),
):
    """Score an AI response."""
    result = quality_scorer.score_response(request.response, request.expected)
    return {"status": "OK", **result}


@router.get("/benchmarks")
async def get_benchmarks(
    user_id: str = Depends(require_admin),
):
    """Get benchmark results."""
    report = benchmark_suite.get_benchmark_report()
    return {"status": "OK", **report}
