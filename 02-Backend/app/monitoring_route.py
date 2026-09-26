"""Monitoring API routes — health, errors, performance, GPU, memory, latency, and uptime."""

from fastapi import APIRouter, Header
from typing import Optional

from app.monitoring import error_tracker, performance_monitor, uptime_tracker
from app.utils.auth.auth_utils import get_user_id_from_token

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
        "latency": performance_monitor.get_latency_metrics(hours=24),
    }


@router.get("/gpu")
async def get_gpu_stats(authorization: str = Header(None)):
    """Get GPU utilization metrics."""
    user_id = get_user_id_from_token(authorization)
    stats = performance_monitor.get_system_stats()
    gpu = stats.get("gpu", {})
    return {
        "status": "OK",
        "gpu": gpu,
        "available": gpu.get("available", False),
    }


@router.get("/memory")
async def get_memory_stats(authorization: str = Header(None)):
    """Get memory usage metrics."""
    user_id = get_user_id_from_token(authorization)
    system = performance_monitor.get_system_stats()
    try:
        import psutil
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "status": "OK",
            "memory": {
                "total_mb": round(vm.total / (1024 * 1024), 2),
                "used_mb": round(vm.used / (1024 * 1024), 2),
                "available_mb": round(vm.available / (1024 * 1024), 2),
                "percent": vm.percent,
                "swap_used_mb": round(swap.used / (1024 * 1024), 2),
                "swap_total_mb": round(swap.total / (1024 * 1024), 2),
                "swap_percent": swap.percent,
            },
        }
    except ImportError:
        return {
            "status": "OK",
            "memory": {
                "total_mb": 0,
                "used_mb": 0,
                "available_mb": 0,
                "percent": 0,
                "swap_used_mb": 0,
                "swap_total_mb": 0,
                "swap_percent": 0,
            },
        }


@router.get("/latency")
async def get_latency_metrics(authorization: str = Header(None), hours: int = 24):
    """Get latency distribution metrics."""
    user_id = get_user_id_from_token(authorization)
    data = performance_monitor.get_latency_metrics(hours=hours)
    return {"status": "OK", "data": data}


@router.get("/api-metrics")
async def get_api_metrics_dashboard(authorization: str = Header(None)):
    """Get API metrics dashboard."""
    user_id = get_user_id_from_token(authorization)
    stats = performance_monitor.get_all_request_stats()
    latency = performance_monitor.get_latency_metrics(hours=24)
    return {
        "status": "OK",
        "requests": stats,
        "latency": latency,
    }
