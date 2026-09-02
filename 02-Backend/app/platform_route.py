"""Unified Platform API routes."""

from fastapi import APIRouter, Header

from .unified_platform import unified_platform
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/api/platform", tags=["platform"])


@router.get("/health")
async def platform_health():
    """Get health of all platform subsystems."""
    health = unified_platform.get_health()
    return {
        "status": "OK",
        "health": {
            "agents": health.agents,
            "workflows": health.workflows,
            "tools": health.tools,
            "memory": health.memory,
            "overall": health.overall,
            "uptime_seconds": health.uptime_seconds,
        },
    }


@router.get("/stats")
async def platform_stats(authorization: str = Header(None)):
    """Get overall platform statistics."""
    user_id = get_user_id_from_token(authorization)
    stats = unified_platform.get_stats()
    return {
        "status": "OK",
        "stats": {
            "total_agents": stats.total_agents,
            "active_agents": stats.active_agents,
            "total_workflows": stats.total_workflows,
            "running_workflows": stats.running_workflows,
            "total_tools": stats.total_tools,
            "uptime_seconds": stats.uptime_seconds,
        },
    }


@router.get("/status")
async def system_status(authorization: str = Header(None)):
    """Get complete system status."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", **unified_platform.get_system_status()}


@router.post("/process")
async def process_request(request: dict, authorization: str = Header(None)):
    """Process a request through the unified platform."""
    user_id = get_user_id_from_token(authorization)
    result = await unified_platform.process_request(request.get("query", ""), user_id)
    return {"status": "OK", **result}
