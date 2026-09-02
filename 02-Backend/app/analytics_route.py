"""Analytics API routes — comprehensive analytics endpoints."""

from fastapi import APIRouter, Header

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


@router.get("/daily")
async def get_daily_usage(
    authorization: str = Header(None),
    days: int = 30,
):
    """Get daily usage counts."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "daily_usage": analytics.get_daily_usage(days=days)}


@router.get("/overview")
async def get_overview(authorization: str = Header(None), days: int = 7):
    """Get platform-wide analytics overview."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_overview(days=days)
    return {"status": "OK", "data": data}


@router.get("/ai-usage")
async def get_ai_usage(authorization: str = Header(None), days: int = 7):
    """Get AI usage analytics."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_ai_usage_analytics(days=days)
    return {"status": "OK", "data": data}


@router.get("/tokens")
async def get_token_analytics(authorization: str = Header(None), days: int = 7):
    """Get token usage analytics."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_token_analytics(days=days)
    return {"status": "OK", "data": data}


@router.get("/costs")
async def get_cost_analytics(authorization: str = Header(None), days: int = 7):
    """Get cost analytics."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_cost_analytics(days=days)
    return {"status": "OK", "data": data}


@router.get("/models")
async def get_model_performance(authorization: str = Header(None), days: int = 7):
    """Get model performance comparison."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_model_performance(days=days)
    return {"status": "OK", "data": data}


@router.get("/search")
async def get_search_analytics(authorization: str = Header(None), days: int = 7):
    """Get search quality metrics."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_search_analytics(days=days)
    return {"status": "OK", "data": data}


@router.get("/knowledge")
async def get_knowledge_analytics(authorization: str = Header(None), days: int = 7):
    """Get knowledge growth metrics."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_knowledge_analytics(days=days)
    return {"status": "OK", "data": data}


@router.get("/workflows")
async def get_workflow_analytics(authorization: str = Header(None), days: int = 7):
    """Get workflow statistics."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_workflow_analytics(days=days)
    return {"status": "OK", "data": data}


@router.get("/agents")
async def get_agent_analytics(authorization: str = Header(None), days: int = 7):
    """Get agent performance metrics."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_agent_analytics(days=days)
    return {"status": "OK", "data": data}


@router.get("/users")
async def get_user_analytics(authorization: str = Header(None), days: int = 7):
    """Get user activity metrics."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_user_analytics(days=days)
    return {"status": "OK", "data": data}


@router.get("/export")
async def export_analytics(authorization: str = Header(None), days: int = 30, format: str = "json"):
    """Export analytics data."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.export_analytics(days=days, format=format)
    return {"status": "OK", "data": data}
