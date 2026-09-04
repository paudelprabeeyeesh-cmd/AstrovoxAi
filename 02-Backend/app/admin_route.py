"""Cost management and compliance API routes.

Security: All endpoints require admin role verification via Principal.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional

from .cost_management import cost_tracker
from .compliance import compliance_manager
from .ai_evaluation import prompt_manager, quality_scorer, benchmark_suite
from .iam import require_admin
from .security_hardening import Principal, get_audit_log

router = APIRouter(prefix="/admin", tags=["admin"])

_audit = get_audit_log()


# Cost Management Routes

@router.get("/costs/usage")
async def get_cost_usage(
    days: int = 30,
    principal: Principal = Depends(require_admin),
):
    """Get cost usage report."""
    _audit.record(actor=principal.id, action="admin_cost_usage", target="costs", outcome="success")
    report = cost_tracker.get_usage_report(principal.id, days)
    return {"status": "OK", **report}


@router.get("/costs/forecast")
async def get_cost_forecast(
    days: int = 30,
    principal: Principal = Depends(require_admin),
):
    """Get cost forecast."""
    _audit.record(actor=principal.id, action="admin_cost_forecast", target="costs", outcome="success")
    forecast = cost_tracker.get_cost_forecast(principal.id, days)
    return {"status": "OK", **forecast}


@router.get("/costs/providers")
async def get_provider_costs(
    principal: Principal = Depends(require_admin),
):
    """Get provider cost comparison."""
    _audit.record(actor=principal.id, action="admin_provider_costs", target="costs", outcome="success")
    comparison = cost_tracker.get_provider_cost_comparison(principal.id)
    return {"status": "OK", "providers": comparison}


# Compliance Routes

@router.post("/compliance/export")
async def request_export(
    principal: Principal = Depends(require_admin),
):
    """Request GDPR data export."""
    _audit.record(actor=principal.id, action="admin_compliance_export", target="compliance", outcome="success")
    export = compliance_manager.request_data_export(principal.id)
    return {
        "status": "OK",
        "export": {"id": export.id, "status": export.status},
    }


@router.post("/compliance/delete")
async def request_deletion(
    principal: Principal = Depends(require_admin),
):
    """Request right-to-delete."""
    _audit.record(actor=principal.id, action="admin_compliance_delete", target="compliance", outcome="success")
    result = compliance_manager.request_data_deletion(principal.id)
    return {"status": "OK", **result}


@router.get("/compliance/status")
async def get_compliance_status(
    principal: Principal = Depends(require_admin),
):
    """Get compliance status."""
    _audit.record(actor=principal.id, action="admin_compliance_status", target="compliance", outcome="success")
    return {
        "status": "OK",
        **compliance_manager.get_compliance_status(principal.id),
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
    principal: Principal = Depends(require_admin),
):
    """Create a prompt version."""
    _audit.record(actor=principal.id, action="admin_create_prompt", target="prompts", outcome="success")
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
    principal: Principal = Depends(require_admin),
):
    """Get active prompt."""
    _audit.record(actor=principal.id, action="admin_get_prompt", target="prompts", outcome="success")
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
    principal: Principal = Depends(require_admin),
):
    """Score an AI response."""
    _audit.record(actor=principal.id, action="admin_score_response", target="evaluation", outcome="success")
    result = quality_scorer.score_response(request.response, request.expected)
    return {"status": "OK", **result}


@router.get("/benchmarks")
async def get_benchmarks(
    principal: Principal = Depends(require_admin),
):
    """Get benchmark results."""
    _audit.record(actor=principal.id, action="admin_get_benchmarks", target="benchmarks", outcome="success")
    report = benchmark_suite.get_benchmark_report()
    return {"status": "OK", **report}
