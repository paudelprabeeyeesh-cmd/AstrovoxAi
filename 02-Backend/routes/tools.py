import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.tool_analytics import tool_analytics
from app.tool_cache import tool_cache
from app.tool_dynamic_loader import dynamic_tool_loader
from app.tool_models import ToolHealthStatus, ToolMetricsResponse, ToolRegistrationRequest
from app.tool_parallel_executor import ParallelToolExecutor
from app.tool_registry import ToolExecutionResult, tool_registry
from app.tool_executor import ToolExecutor
from app.webhooks.manager import webhook_manager
from app.plugin_marketplace import plugin_marketplace
from sandboxing.tool_metrics import tool_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolListResponse(BaseModel):
    tools: List[Dict[str, Any]]


class ToolHealthResponse(BaseModel):
    name: str
    status: ToolHealthStatus
    metrics: Optional[ToolMetricsResponse] = None


class ParallelExecuteRequest(BaseModel):
    calls: List[Dict[str, Any]]
    user_id: str
    max_workers: int = 8


class ParallelExecuteResponse(BaseModel):
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    user_id: str
    use_cache: bool = True
    cache_ttl: Optional[int] = None


class ToolExecuteResponse(BaseModel):
    tool_name: str
    result: str
    status: str
    duration_ms: float
    cached: bool = False
    error: Optional[str] = None


class DynamicLoadRequest(BaseModel):
    module_path: str
    attribute: str = "tool_spec"


class DynamicLoadResponse(BaseModel):
    name: str
    source: str
    loaded: bool


class PluginSearchRequest(BaseModel):
    query: str = ""
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 20


class WebhookRegisterRequest(BaseModel):
    url: str
    events: List[str]
    secret: str = ""
    headers: Dict[str, str] = {}
    owner_id: str = ""


class WebhookDeliveryResponse(BaseModel):
    delivery_id: str
    endpoint_id: str
    event_type: str
    status: str
    attempts: int
    delivered_at: Optional[float] = None
    error: Optional[str] = None


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
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": {},
                "required_permissions": t.get("required_permissions", []),
                "tags": t.get("tags", []),
                "version": t.get("version", "1.0.0"),
                "deprecated": t.get("deprecated", False),
                "health": health,
            }
        )
    return ToolListResponse(tools=tools)


@router.get("/{tool_name}", response_model=Dict[str, Any])
async def get_tool(tool_name: str):
    t = tool_registry.get(tool_name)
    if not t:
        raise HTTPException(status_code=404, detail="Tool not found")
    metrics = tool_metrics.get(tool_name)
    health = metrics.health_status if metrics else ToolHealthStatus.UNKNOWN
    return {
        "name": getattr(t, "name", tool_name),
        "description": getattr(t, "description", ""),
        "parameters": getattr(t, "parameters", {}),
        "required_permissions": getattr(t, "required_permissions", []),
        "tags": getattr(t, "tags", []),
        "version": getattr(t, "version", "1.0.0"),
        "deprecated": getattr(t, "deprecated", False),
        "owner": getattr(t, "owner", None),
        "timeout_seconds": getattr(t, "timeout_seconds", 30.0),
        "health": health,
    }


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: ToolExecuteRequest):
    execution = tool_registry.execute(
        tool_name=request.tool_name,
        arguments=request.arguments,
        user_id=request.user_id,
        use_cache=request.use_cache,
        cache_ttl=request.cache_ttl,
    )
    return ToolExecuteResponse(
        tool_name=execution.tool_name,
        result=execution.result,
        status=execution.status,
        duration_ms=execution.duration_ms,
        cached=execution.cached,
        error=execution.error,
    )


@router.post("/execute-parallel", response_model=ParallelExecuteResponse)
async def execute_tools_parallel(request: ParallelExecuteRequest):
    executor = ToolExecutor()
    parallel_results = executor.execute_parallel(
        request.calls,
        request.user_id,
        max_workers=request.max_workers,
    )
    results = [
        {
            "tool_name": r.get("tool_name"),
            "result": r.get("result"),
            "status": r.get("status"),
            "error": r.get("error"),
            "duration_ms": r.get("duration_ms"),
        }
        for r in parallel_results
    ]
    success = sum(1 for r in results if r["status"] == "success")
    total = len(results)
    return ParallelExecuteResponse(
        results=results,
        summary={
            "total_calls": total,
            "success_count": success,
            "failure_count": total - success,
            "success_rate": round(success / total, 4) if total else 0.0,
        },
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


@router.get("/analytics/report")
async def get_tools_analytics_report():
    report = tool_analytics.generate_report()
    return report.to_dict()


@router.get("/analytics/leaderboard")
async def get_tools_leaderboard(metric: str = "total_calls", limit: int = 10):
    return tool_analytics.get_tool_leaderboard(metric=metric, limit=limit)


@router.get("/analytics/health-distribution")
async def get_tools_health_distribution():
    return tool_analytics.get_health_distribution()


@router.get("/analytics/slowest")
async def get_slowest_tools(limit: int = 10):
    return tool_analytics.get_slowest_tools(limit=limit)


@router.post("/cache/clear")
async def clear_tool_cache():
    tool_cache.clear()
    return {"status": "cleared"}


@router.get("/cache/stats")
async def get_tool_cache_stats():
    return tool_cache.get_stats()


@router.post("/dynamic/load", response_model=DynamicLoadResponse)
async def dynamically_load_tool(request: DynamicLoadRequest):
    spec = tool_registry.load_from_source(request.module_path, attribute=request.attribute)
    return DynamicLoadResponse(
        name=spec.name if spec else "",
        source=request.module_path,
        loaded=spec is not None,
    )


@router.get("/dynamic/loaded")
async def list_dynamically_loaded_tools():
    return dynamic_tool_loader.get_loaded_tools()


@router.delete("/dynamic/{tool_name}")
async def unload_dynamic_tool(tool_name: str):
    success = dynamic_tool_loader.unload(tool_name)
    if not success:
        raise HTTPException(status_code=404, detail="Dynamic tool not found")
    return {"status": "unloaded", "tool_name": tool_name}


@router.get("/discover")
async def discover_tools(query: str = "", limit: int = 20):
    return tool_registry.search(query, limit=limit)


@router.post("/plugins/search")
async def search_plugin_marketplace(request: PluginSearchRequest):
    results = plugin_marketplace.search(
        query=request.query,
        category=request.category,
        tags=request.tags,
        limit=request.limit,
    )
    return [
        {
            "listing_id": r.listing_id,
            "name": r.name,
            "description": r.description,
            "author_name": r.author_name,
            "version": r.version,
            "category": r.category,
            "tags": r.tags,
            "downloads": r.downloads,
            "rating": r.rating,
            "status": r.status.value,
        }
        for r in results
    ]


@router.get("/plugins/categories")
async def list_plugin_categories():
    stats = plugin_marketplace.get_stats()
    return {"categories": stats.get("categories", [])}


@router.post("/webhooks/endpoints", response_model=Dict[str, Any])
async def register_webhook_endpoint(request: WebhookRegisterRequest):
    endpoint = webhook_manager.register_endpoint(
        url=request.url,
        events=request.events,
        secret=request.secret,
        headers=request.headers,
        owner_id=request.owner_id,
    )
    return {
        "endpoint_id": endpoint.endpoint_id,
        "url": endpoint.url,
        "events": endpoint.events,
        "active": endpoint.active,
    }


@router.get("/webhooks/endpoints")
async def list_webhook_endpoints(owner_id: Optional[str] = None):
    endpoints = webhook_manager.list_endpoints(owner_id=owner_id)
    return [
        {
            "endpoint_id": ep.endpoint_id,
            "url": ep.url,
            "events": ep.events,
            "active": ep.active,
            "created_at": ep.created_at,
        }
        for ep in endpoints
    ]


@router.get("/webhooks/deliveries")
async def get_webhook_deliveries(endpoint_id: Optional[str] = None):
    stats = webhook_manager.get_delivery_stats(endpoint_id=endpoint_id)
    return stats


@router.get("/webhooks/dead-letters")
async def get_webhook_dead_letters(endpoint_id: Optional[str] = None):
    dl = webhook_manager.get_dead_letters(endpoint_id=endpoint_id)
    return [
        {
            "delivery_id": d.delivery_id,
            "endpoint_id": d.endpoint_id,
            "event_type": d.event_type,
            "error": d.error,
            "attempts": d.attempts,
            "created_at": d.created_at,
        }
        for d in dl
    ]


@router.post("/webhooks/deliveries/{delivery_id}/retry")
async def retry_webhook_delivery(delivery_id: str):
    delivery = webhook_manager.retry_delivery(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found or not retryable")
    return {"status": "requeued", "delivery_id": delivery_id}
