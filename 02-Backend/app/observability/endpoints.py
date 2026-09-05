"""Health check endpoints for the AstrovoxAi API."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import asyncio

from app.observability import get_observability, HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    obs = get_observability()
    overall_status = obs.health.get_overall_status()
    
    return {
        "status": overall_status.value,
        "timestamp": asyncio.get_event_loop().time(),
        "service": "astrovoxai"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with all subsystem status."""
    obs = get_observability()
    status = obs.get_status()
    
    # Determine HTTP status code based on health
    health_status = HealthStatus(status["health"]["status"])
    if health_status == HealthStatus.HEALTHY:
        status_code = 200
    elif health_status == HealthStatus.DEGRADED:
        status_code = 200  # Still return 200 for degraded
    else:
        status_code = 503  # Service unavailable for unhealthy
    
    return status


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    obs = get_observability()
    overall_status = obs.health.get_overall_status()
    
    # Ready if not unhealthy (degraded is still ready)
    if overall_status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    # Simple liveness - if we're responding, we're alive
    return {"status": "alive"}


@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    obs = get_observability()
    return obs.get_metrics_prometheus()


@router.get("/alerts")
async def alerts_endpoint():
    """Get current alerts."""
    obs = get_observability()
    active_alerts = obs.alerts.get_active_alerts()
    
    return {
        "active_alerts": [
            {
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status,
                "labels": alert.labels,
                "annotations": alert.annotations,
                "starts_at": alert.starts_at,
                "ends_at": alert.ends_at
            }
            for alert in active_alerts
        ],
        "count": len(active_alerts)
    }