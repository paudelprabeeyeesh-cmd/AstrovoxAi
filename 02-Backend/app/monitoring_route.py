"""Monitoring API routes — health, errors, performance, and uptime."""

from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional

from .monitoring import error_tracker, performance_monitor, uptime_tracker
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with system stats."""
    system_stats = performance_monitor.get_system_stats()
    uptime = uptime_tracker.get_uptime()
    error_summary = error_tracker.get_error_summary()

    return {
        "status": "healthy",
        "timestamp": uptime["start_time"],
        "uptime": uptime,
        "system": system_stats,
        "errors": error_summary,
    }


@router.get("/errors")
async def get_errors(
    authorization: str = Header(None),
    limit: int = 50,
    severity: Optional[str] = None,
):
    """Get tracked errors."""
    user_id = get_user_id_from_token(authorization)
    errors = error_tracker.get_errors(severity=severity, limit=limit)

    return {
        "status": "OK",
        "errors": [
            {
                "error_type": e.error_type,
                "message": e.message,
                "endpoint": e.endpoint,
                "timestamp": e.timestamp,
                "severity": e.severity,
            }
            for e in errors
        ],
        "summary": error_tracker.get_error_summary(),
    }


@router.get("/performance")
async def get_performance(authorization: str = Header(None)):
    """Get performance statistics."""
    user_id = get_user_id_from_token(authorization)

    return {
        "status": "OK",
        "system": performance_monitor.get_system_stats(),
        "requests": performance_monitor.get_all_request_stats(),
    }


@router.get("/uptime")
async def get_uptime():
    """Get application uptime."""
    return {"status": "OK", **uptime_tracker.get_uptime()}


@router.get("/dashboard")
async def get_monitoring_dashboard(authorization: str = Header(None)):
    """Get complete monitoring dashboard."""
    user_id = get_user_id_from_token(authorization)

    return {
        "status": "OK",
        "uptime": uptime_tracker.get_uptime(),
        "system": performance_monitor.get_system_stats(),
        "errors": error_tracker.get_error_summary(),
        "requests": performance_monitor.get_all_request_stats(),
    }
