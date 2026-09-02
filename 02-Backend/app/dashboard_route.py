"""Dashboard API routes for UI."""

from fastapi import APIRouter, Header

from .dashboard import dashboard_service
from .multi_agent import agent_orchestrator
from .workflow_engine import workflow_engine
from .tool_execution import tool_executor
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(authorization: str = Header(None)):
    """Get platform statistics."""
    user_id = get_user_id_from_token(authorization)
    stats = dashboard_service.get_stats()
    return {
        "status": "OK",
        "stats": {
            "total_agents": stats.total_agents,
            "active_agents": stats.active_agents,
            "total_tasks": stats.total_tasks,
            "completed_tasks": stats.completed_tasks,
            "running_workflows": stats.running_workflows,
            "uptime_seconds": stats.uptime_seconds,
        },
    }


@router.get("/tasks")
async def get_running_tasks(authorization: str = Header(None)):
    """Get running tasks."""
    user_id = get_user_id_from_token(authorization)
    tasks = dashboard_service.get_running_tasks()
    return {
        "status": "OK",
        "tasks": [
            {
                "id": t.id,
                "name": t.name,
                "agent": t.agent,
                "status": t.status,
                "progress": t.progress,
            }
            for t in tasks
        ],
    }


@router.get("/workflows")
async def get_workflow_status(authorization: str = Header(None)):
    """Get workflow status."""
    user_id = get_user_id_from_token(authorization)
    workflows = dashboard_service.get_workflow_status()
    return {
        "status": "OK",
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "status": w.status,
                "progress": w.progress,
                "total_steps": w.total_steps,
                "completed_steps": w.completed_steps,
            }
            for w in workflows
        ],
    }


@router.get("/agents")
async def get_agents(authorization: str = Header(None)):
    """Get agent information."""
    user_id = get_user_id_from_token(authorization)
    analytics = agent_orchestrator.get_analytics()
    return {"status": "OK", **analytics}


@router.get("/tools")
async def get_tools(authorization: str = Header(None)):
    """Get tool information."""
    user_id = get_user_id_from_token(authorization)
    tools = tool_executor.registry.list_tools()
    return {"status": "OK", "tools": tools}


@router.get("/logs")
async def get_logs(authorization: str = Header(None), limit: int = 50):
    """Get recent logs."""
    user_id = get_user_id_from_token(authorization)
    logs = dashboard_service.get_agent_logs(limit)
    return {
        "status": "OK",
        "logs": [
            {
                "timestamp": l.timestamp,
                "level": l.level,
                "source": l.source,
                "message": l.message,
            }
            for l in logs
        ],
    }


@router.get("/timeline")
async def get_timeline(authorization: str = Header(None), limit: int = 100):
    """Get execution timeline."""
    user_id = get_user_id_from_token(authorization)
    events = dashboard_service.get_timeline(limit)
    return {
        "status": "OK",
        "events": [
            {
                "timestamp": e.timestamp,
                "type": e.event_type,
                "description": e.description,
                "source": e.source,
            }
            for e in events
        ],
    }


@router.get("/metrics")
async def get_metrics(authorization: str = Header(None)):
    """Get tool execution metrics."""
    user_id = get_user_id_from_token(authorization)
    metrics = tool_executor.get_metrics()
    return {"status": "OK", "metrics": metrics}
