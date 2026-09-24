import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.tool_registry import tool_registry
from app.tool_models import (
    ToolDefinitionModel,
    ToolHealthStatus,
    ToolMetricsResponse,
    ToolRegistrationRequest,
)
from sandboxing.tool_metrics import tool_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolListResponse(BaseModel):
    tools: List[ToolDefinitionModel]


class ToolHealthResponse(BaseModel):
    name: str
    status: ToolHealthStatus
    metrics: Optional[ToolMetricsResponse] = None


@router.get("/", response_model=ToolListResponse)
async def list_tools(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    deprecated: Optional[bool] = Query(None, description="Filter deprecated status"),
):
    all_tools = tool_registry.list_all()
    tools = []
    for t in all_tools:
        if tag and tag not in t.get("tags", []):
            continue
        if deprecated is not None and t.get("deprecated", False) != deprecated:
            continue
        metrics = tool_metrics.get(t["name"])
        health = metrics.health_status if metrics else ToolHealthStatus.UNKNOWN
        tools.append(
            ToolDefinitionModel(
                name=t["name"],
                description=t.get("description", ""),
                parameters={},
                required_permissions=t.get("required_permissions", []),
                tags=t.get("tags", []),
                version=t.get("version", "1.0.0"),
                deprecated=t.get("deprecated", False),
                health=health,
            )
        )
    return ToolListResponse(tools=tools)


@router.get("/{tool_name}", response_model=ToolDefinitionModel)
async def get_tool(tool_name: str):
    t = tool_registry.get(tool_name)
    if not t:
        raise HTTPException(status_code=404, detail="Tool not found")
    metrics = tool_metrics.get(tool_name)
    health = metrics.health_status if metrics else ToolHealthStatus.UNKNOWN
    return ToolDefinitionModel(
        name=getattr(t, "name", tool_name),
        description=getattr(t, "description", ""),
        parameters=getattr(t, "parameters", {}),
        required_permissions=getattr(t, "required_permissions", []),
        tags=getattr(t, "tags", []),
        version=getattr(t, "version", "1.0.0"),
        deprecated=getattr(t, "deprecated", False),
        health=health,
    )


@router.get("/{tool_name}/metrics", response_model=ToolMetricsResponse)
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
        health_status=ToolHealthStatus(m.health_status),
        pending_approvals=m.pending_approvals,
        circuit_breaker_rejections=m.circuit_breaker_rejections,
        last_call_at=m.last_call_at,
    )


@router.get("/{tool_name}/health", response_model=ToolHealthResponse)
async def get_tool_health(tool_name: str):
    m = tool_metrics.get(tool_name)
    if not m:
        raise HTTPException(status_code=404, detail="No metrics for tool")
    return ToolHealthResponse(
        name=tool_name,
        status=ToolHealthStatus(m.health_status),
        metrics=ToolMetricsResponse(
            tool_name=m.tool_name,
            total_calls=m.total_calls,
            success_count=m.success_count,
            failure_count=m.failure_count,
            avg_duration_ms=m.avg_duration_ms,
            error_rate=m.error_rate,
            health_status=ToolHealthStatus(m.health_status),
            pending_approvals=m.pending_approvals,
            circuit_breaker_rejections=m.circuit_breaker_rejections,
            last_call_at=m.last_call_at,
        ),
    )


@router.get("/health/overview")
async def get_tools_health_overview():
    all_metrics = tool_metrics.get_all()
    summary = {
        "total_tools": len(all_metrics),
        "healthy": sum(1 for m in all_metrics.values() if m.health_status == "healthy"),
        "degraded": sum(1 for m in all_metrics.values() if m.health_status == "degraded"),
        "unhealthy": sum(1 for m in all_metrics.values() if m.health_status == "unhealthy"),
        "unknown": sum(1 for m in all_metrics.values() if m.health_status == "unknown"),
    }
    return summary
