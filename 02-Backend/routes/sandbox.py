import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from sandboxing.tool_sandbox import ToolSandbox, ToolSandboxStatus
from sandboxing.tool_sandbox_models import (
    ToolApproveRequest,
    ToolApproveResponse,
    ToolExecuteRequest,
    ToolExecuteResponse,
)
from sandboxing.approval_store import approval_store
from sandboxing.tool_metrics import tool_metrics
from app.tool_executor import ToolExecutor
from app.circuit_breaker import CircuitBreaker
from app.audit import audit_logger
from app.tool_models import ApprovalSummary, ToolMetricsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

tool_executor = ToolExecutor()
tool_circuit_breaker = CircuitBreaker(
    name="tool_executor",
    failure_threshold=5,
    recovery_timeout=30,
    success_threshold=3,
)
tool_sandbox = ToolSandbox(
    tool_executor=tool_executor,
    tool_circuit_breaker=tool_circuit_breaker,
    max_retries=2,
    approval_ttl_seconds=300.0,
)


def _extract_user_id(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    try:
        from app.auth import supabase
        token = authorization.replace("Bearer ", "")
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return response.user.id
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: ToolExecuteRequest, authorization: Optional[str] = None):
    user_id = _extract_user_id(authorization)
    result = tool_sandbox.execute(request.tool_name, request.arguments, user_id)
    return ToolExecuteResponse(
        status=result.status,
        output=result.output,
        error=result.error,
        approval_id=result.approval_id,
        message=getattr(result, "message", None),
        details=result.details,
    )


@router.post("/approve", response_model=ToolApproveResponse)
async def approve_tool(request: ToolApproveRequest, authorization: Optional[str] = None):
    user_id = _extract_user_id(authorization)
    result = tool_sandbox.approve(request.approval_id, user_id)
    if result is None:
        raise HTTPException(status_code=400, detail="Approval failed")
    return ToolApproveResponse(
        status=result.status,
        output=result.output,
        error=result.error,
        details=result.details,
    )


@router.post("/reject", response_model=ToolApproveResponse)
async def reject_tool(request: ToolApproveRequest, authorization: Optional[str] = None):
    user_id = _extract_user_id(authorization)
    result = tool_sandbox.reject(request.approval_id, user_id)
    if result is None:
        raise HTTPException(status_code=400, detail="Rejection failed")
    return ToolApproveResponse(
        status=result.status,
        output=result.output,
        error=result.error,
        details=result.details,
    )


@router.get("/approvals/pending", response_model=List[ApprovalSummary])
async def list_pending_approvals(_: str = Depends(_extract_user_id)):
    pending = approval_store.list_pending()
    now = time.time() if 'time' in globals() else __import__('time').time()
    return [
        ApprovalSummary(
            approval_id=a.approval_id,
            tool_name=a.tool_name,
            arguments=a.arguments,
            user_id=a.user_id,
            tier=a.tier,
            operation=a.operation,
            status=a.status,
            created_at=a.created_at,
            ttl_seconds=a.ttl_seconds,
            remaining_ttl=max(0, a.ttl_seconds - (now - a.created_at)) if a.created_at else None,
        )
        for a in pending
    ]


@router.get("/approvals/history", response_model=List[ApprovalSummary])
async def list_approval_history(limit: int = Query(100, ge=1, le=1000)):
    history = approval_store.list_history(limit=limit)
    return [
        ApprovalSummary(
            approval_id=a.approval_id,
            tool_name=a.tool_name,
            arguments=a.arguments,
            user_id=a.user_id,
            tier=a.tier,
            operation=a.operation,
            status=a.status,
            created_at=a.created_at,
            ttl_seconds=a.ttl_seconds,
        )
        for a in history
    ]


@router.get("/approvals/stats")
async def get_approval_stats():
    return approval_store.get_stats()


@router.get("/metrics/tools", response_model=List[ToolMetricsResponse])
async def list_tool_metrics():
    all_metrics = tool_metrics.get_all()
    return [
        ToolMetricsResponse(
            tool_name=m.tool_name,
            total_calls=m.total_calls,
            success_count=m.success_count,
            failure_count=m.failure_count,
            avg_duration_ms=m.avg_duration_ms,
            error_rate=m.error_rate,
            health_status=m.health_status,
            pending_approvals=m.pending_approvals,
            circuit_breaker_rejections=m.circuit_breaker_rejections,
            last_call_at=m.last_call_at,
        )
        for m in all_metrics.values()
    ]


@router.get("/metrics/tools/{tool_name}", response_model=ToolMetricsResponse)
async def get_tool_metrics(tool_name: str):
    m = tool_metrics.get(tool_name)
    if not m:
        raise HTTPException(status_code=404, detail="No metrics for tool")
    return ToolMetricsResponse(
        tool_name=m.tool_name,
        total_calls=m.total_calls,
        success_count=m.success_count,
        failure_count=m.failure_count,
        avg_duration_ms=m.avg_duration_ms,
        error_rate=m.error_rate,
        health_status=m.health_status,
        pending_approvals=m.pending_approvals,
        circuit_breaker_rejections=m.circuit_breaker_rejections,
        last_call_at=m.last_call_at,
    )


@router.post("/cleanup/expired")
async def cleanup_expired_approvals(_: str = Depends(_extract_user_id)):
    approval_store.cleanup_expired()
    return {"status": "cleaned up expired approvals"}
