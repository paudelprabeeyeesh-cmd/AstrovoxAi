"""Analytics API routes — dashboard data and usage statistics."""

from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional

from .analytics import analytics
from .auth_utils import get_user_id_from_token

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard(authorization: str = Header(None)):
    """Get analytics dashboard data."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "data": analytics.get_dashboard_data()}


@router.get("/usage")
async def get_usage(
    authorization: str = Header(None),
    days: int = 7,
):
    """Get usage statistics."""
    user_id = get_user_id_from_token(authorization)
    stats = analytics.get_usage_stats(days=days)
    return {
        "status": "OK",
        "usage": {
            "total_requests": stats.total_requests,
            "total_tokens": stats.total_tokens,
            "average_latency": round(stats.average_latency, 3),
            "error_rate": round(stats.error_rate, 4),
            "active_users": stats.active_users,
            "total_users": stats.total_users,
        },
    }


@router.get("/providers")
async def get_provider_breakdown(authorization: str = Header(None)):
    """Get provider usage breakdown."""
    user_id = get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "providers": analytics.get_provider_breakdown(),
        "models": analytics.get_model_breakdown(),
    }


@router.get("/costs")
async def get_cost_estimate(authorization: str = Header(None)):
    """Get estimated costs."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "costs": analytics.get_cost_estimate()}


@router.get("/daily")
async def get_daily_usage(
    authorization: str = Header(None),
    days: int = 30,
):
    """Get daily usage counts."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "daily_usage": analytics.get_daily_usage(days=days)}
