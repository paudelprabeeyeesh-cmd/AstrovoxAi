"""Analytics API routes — comprehensive analytics endpoints."""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, Header, Query, Body

from .analytics import analytics, advanced_analytics
from app.utils.auth.auth_utils import get_user_id_from_token

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard(authorization: str = Header(None), days: int = 7):
    """Get analytics dashboard data."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "data": analytics.get_dashboard_data(days=days)}


@router.get("/usage")
async def get_usage(authorization: str = Header(None), days: int = 7):
    """Get usage statistics."""
    user_id = get_user_id_from_token(authorization)
    stats = analytics.get_usage_stats(days=days)
    return {
        "status": "OK",
        "usage": {
            "total_requests": stats["total_requests"],
            "total_tokens": stats["total_tokens"],
            "average_latency": round(stats["average_latency"], 3),
            "error_rate": round(stats["error_rate"], 4),
            "active_users": stats["active_users"],
            "total_users": stats["total_users"],
        },
    }


@router.get("/providers")
async def get_provider_breakdown(authorization: str = Header(None)):
    """Get provider usage breakdown."""
    user_id = get_user_id_from_token(authorization)
    return {
        "status": "OK",
        "providers": advanced_analytics.get_usage_stats().get("provider_breakdown", {}),
        "models": advanced_analytics.get_usage_stats().get("model_breakdown", {}),
    }


@router.get("/daily")
async def get_daily_usage(authorization: str = Header(None), days: int = 30):
    """Get daily usage counts."""
    user_id = get_user_id_from_token(authorization)
    cutoff = time.time() - (days * 86400)
    daily: dict[str, int] = {}
    for e in advanced_analytics._events:
        if e.timestamp >= cutoff and e.event_type == "ai_request":
            day = datetime.fromtimestamp(e.timestamp).strftime("%Y-%m-%d")
            daily[day] = daily.get(day, 0) + 1
    return {"status": "OK", "daily_usage": daily}


@router.get("/overview")
async def get_overview(authorization: str = Header(None), days: int = 7):
    """Get platform-wide analytics overview."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.get_dashboard_data(days=days)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 1. Real-time analytics
# ------------------------------------------------------------------
@router.get("/realtime")
async def get_realtime_analytics(authorization: str = Header(None), days: int = 1):
    """Get real-time analytics dashboard."""
    user_id = get_user_id_from_token(authorization)
    data = advanced_analytics.get_realtime_dashboard(days=days)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 2. User behavior analytics
# ------------------------------------------------------------------
@router.post("/behavior")
async def track_behavior(authorization: str = Header(None), payload: dict = Body(...)):
    """Track a user behavior event."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import BehaviorEvent
    event = BehaviorEvent(
        user_id=user_id,
        session_id=payload.get("session_id", ""),
        event_type=payload.get("event_type", "unknown"),
        page_url=payload.get("page_url", ""),
        element_id=payload.get("element_id", ""),
        element_class=payload.get("element_class", ""),
        properties=payload.get("properties", {}),
        time_on_page_seconds=payload.get("time_on_page_seconds", 0),
        scroll_depth_percent=payload.get("scroll_depth_percent", 0),
        timestamp=payload.get("timestamp", time.time()),
    )
    advanced_analytics.track_behavior(event)
    return {"status": "OK"}


@router.get("/behavior")
async def get_behavior_analytics(authorization: str = Header(None), days: int = 7, user_id: Optional[str] = None):
    """Get user behavior analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_user_behavior_analytics(days=days, user_id=user_id)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 3. Token usage analytics
# ------------------------------------------------------------------
@router.get("/tokens")
async def get_token_analytics(authorization: str = Header(None), days: int = 7, user_id: Optional[str] = None):
    """Get token usage analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_token_analytics(days=days, user_id=user_id)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 4. Cost analytics
# ------------------------------------------------------------------
@router.get("/costs")
async def get_cost_analytics(authorization: str = Header(None), days: int = 7, user_id: Optional[str] = None):
    """Get cost analytics and billing insights."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_cost_analytics(days=days, user_id=user_id)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 5. Performance analytics
# ------------------------------------------------------------------
@router.get("/performance")
async def get_performance_analytics(authorization: str = Header(None), days: int = 7, user_id: Optional[str] = None):
    """Get performance analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_performance_analytics(days=days, user_id=user_id)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 6. Error rate analytics
# ------------------------------------------------------------------
@router.get("/errors")
async def get_error_analytics(authorization: str = Header(None), days: int = 7, user_id: Optional[str] = None):
    """Get error rate analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_error_analytics(days=days, user_id=user_id)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 7. Feature adoption analytics
# ------------------------------------------------------------------
@router.post("/feature-adoption")
async def track_feature_adoption(authorization: str = Header(None), payload: dict = Body(...)):
    """Track feature adoption event."""
    user_id = get_user_id_from_token(authorization)
    feature_name = payload.get("feature_name", "unknown")
    category = payload.get("category", "general")
    advanced_analytics.track_feature_use(user_id, feature_name, category)
    return {"status": "OK"}


@router.get("/feature-adoption")
async def get_feature_adoption(authorization: str = Header(None), days: int = 30):
    """Get feature adoption analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_feature_adoption_analytics(days=days)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 8. Conversation analytics
# ------------------------------------------------------------------
@router.post("/conversations")
async def track_conversation(authorization: str = Header(None), payload: dict = Body(...)):
    """Track a conversation."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import ConversationRecord
    conv = ConversationRecord(
        conversation_id=payload.get("conversation_id", ""),
        user_id=user_id,
        model=payload.get("model", ""),
        provider=payload.get("provider", ""),
        message_count=payload.get("message_count", 0),
        total_tokens=payload.get("total_tokens", 0),
        total_cost=payload.get("total_cost", 0.0),
        duration_seconds=payload.get("duration_seconds", 0.0),
        started_at=payload.get("started_at", time.time()),
        ended_at=payload.get("ended_at", time.time()),
        sentiment=payload.get("sentiment", "neutral"),
        satisfaction_score=payload.get("satisfaction_score"),
    )
    advanced_analytics.track_conversation(conv)
    return {"status": "OK"}


@router.get("/conversations")
async def get_conversation_analytics(authorization: str = Header(None), days: int = 7, user_id: Optional[str] = None):
    """Get conversation analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_conversation_analytics(days=days, user_id=user_id)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 9. Model performance comparison
# ------------------------------------------------------------------
@router.get("/models")
async def get_model_performance(authorization: str = Header(None), days: int = 7):
    """Get model performance comparison."""
    user_id = get_user_id_from_token(authorization)
    data = advanced_analytics.get_model_performance_comparison(days=days)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 10. A/B test analytics
# ------------------------------------------------------------------
@router.post("/ab-tests")
async def create_ab_test(authorization: str = Header(None), payload: dict = Body(...)):
    """Create an A/B test."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import ABTestRecord
    test = ABTestRecord(
        test_id=payload.get("test_id", str(uuid.uuid4())),
        test_name=payload["test_name"],
        description=payload.get("description", ""),
        variant_a=payload.get("variant_a", {}),
        variant_b=payload.get("variant_b", {}),
        status=payload.get("status", "draft"),
        metric_name=payload["metric_name"],
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        min_sample_size=payload.get("min_sample_size", 100),
        confidence_level=payload.get("confidence_level", 0.95),
        created_by=user_id,
    )
    advanced_analytics.create_ab_test(test)
    return {"status": "OK", "test_id": test.test_id}


@router.post("/ab-tests/{test_id}/assign")
async def assign_ab_test(test_id: str, authorization: str = Header(None), payload: dict = Body(...)):
    """Assign a user to an A/B test variant."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import ABTestAssignment
    assignment = ABTestAssignment(
        test_id=test_id,
        user_id=user_id,
        variant=payload.get("variant", "A"),
        assigned_at=time.time(),
    )
    advanced_analytics.assign_ab_test(assignment)
    return {"status": "OK"}


@router.post("/ab-tests/{test_id}/events")
async def track_ab_event(test_id: str, authorization: str = Header(None), payload: dict = Body(...)):
    """Track an A/B test event."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import ABTestEvent
    event = ABTestEvent(
        test_id=test_id,
        user_id=user_id,
        variant=payload.get("variant", "A"),
        event_name=payload["event_name"],
        event_value=payload.get("event_value"),
        properties=payload.get("properties", {}),
        timestamp=payload.get("timestamp", time.time()),
    )
    advanced_analytics.track_ab_event(event)
    return {"status": "OK"}


@router.get("/ab-tests/{test_id}")
async def get_ab_test_analytics(test_id: str, authorization: str = Header(None)):
    """Get A/B test analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_ab_test_analytics(test_id=test_id)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 11. Cohort analysis
# ------------------------------------------------------------------
@router.post("/cohorts")
async def create_cohort(authorization: str = Header(None), payload: dict = Body(...)):
    """Create a cohort."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import CohortRecord
    cohort = CohortRecord(
        cohort_id=payload.get("cohort_id", str(uuid.uuid4())),
        cohort_name=payload["cohort_name"],
        description=payload.get("description", ""),
        definition=payload["definition"],
        created_by=user_id,
    )
    advanced_analytics.create_cohort(cohort)
    return {"status": "OK", "cohort_id": cohort.cohort_id}


@router.post("/cohorts/{cohort_id}/members")
async def add_cohort_member(cohort_id: str, authorization: str = Header(None), payload: dict = Body(...)):
    """Add a member to a cohort."""
    get_user_id_from_token(authorization)
    from app.analytics.advanced import CohortMember
    member = CohortMember(
        cohort_id=cohort_id,
        user_id=payload["user_id"],
        joined_at=payload.get("joined_at", time.time()),
        is_active=payload.get("is_active", True),
    )
    advanced_analytics.add_cohort_member(member)
    return {"status": "OK"}


@router.get("/cohorts/{cohort_id}")
async def get_cohort_analysis(cohort_id: str, authorization: str = Header(None), days: int = 30):
    """Get cohort analysis."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_cohort_analysis(cohort_id=cohort_id, days=days)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 12. Funnel analysis
# ------------------------------------------------------------------
@router.post("/funnels")
async def create_funnel(authorization: str = Header(None), payload: dict = Body(...)):
    """Create a funnel."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import FunnelRecord
    funnel = FunnelRecord(
        funnel_id=payload.get("funnel_id", str(uuid.uuid4())),
        funnel_name=payload["funnel_name"],
        description=payload.get("description", ""),
        steps=payload["steps"],
        is_active=payload.get("is_active", True),
    )
    advanced_analytics.create_funnel(funnel)
    return {"status": "OK", "funnel_id": funnel.funnel_id}


@router.post("/funnels/{funnel_id}/events")
async def track_funnel_event(funnel_id: str, authorization: str = Header(None), payload: dict = Body(...)):
    """Track a funnel event."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import FunnelEvent
    event = FunnelEvent(
        funnel_id=funnel_id,
        user_id=user_id,
        session_id=payload.get("session_id", ""),
        step_index=payload["step_index"],
        step_name=payload["step_name"],
        entered_at=payload.get("entered_at", time.time()),
        exited_at=payload.get("exited_at"),
        completed=payload.get("completed", False),
        drop_off_reason=payload.get("drop_off_reason", ""),
        properties=payload.get("properties", {}),
    )
    advanced_analytics.track_funnel_event(event)
    return {"status": "OK"}


@router.get("/funnels/{funnel_id}")
async def get_funnel_analytics(funnel_id: str, authorization: str = Header(None), days: int = 30):
    """Get funnel analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_funnel_analytics(funnel_id=funnel_id, days=days)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 13. Retention analytics
# ------------------------------------------------------------------
@router.post("/retention")
async def update_retention(authorization: str = Header(None), payload: dict = Body(...)):
    """Update a retention snapshot."""
    get_user_id_from_token(authorization)
    from app.analytics.advanced import RetentionSnapshot
    snapshot = RetentionSnapshot(
        user_id=payload["user_id"],
        cohort_date=payload["cohort_date"],
        day_0=payload.get("day_0", True),
        day_1=payload.get("day_1", False),
        day_3=payload.get("day_3", False),
        day_7=payload.get("day_7", False),
        day_14=payload.get("day_14", False),
        day_30=payload.get("day_30", False),
        day_60=payload.get("day_60", False),
        day_90=payload.get("day_90", False),
        last_active_date=payload.get("last_active_date"),
    )
    advanced_analytics.update_retention_snapshot(snapshot)
    return {"status": "OK"}


@router.get("/retention")
async def get_retention_analytics(authorization: str = Header(None), cohort_date: str = Query(...), days: int = 90):
    """Get retention analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_retention_analytics(cohort_date=cohort_date, days=days)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 14. Revenue analytics
# ------------------------------------------------------------------
@router.post("/revenue")
async def track_revenue(authorization: str = Header(None), payload: dict = Body(...)):
    """Track a revenue event."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import RevenueEvent
    event = RevenueEvent(
        user_id=user_id,
        event_type=payload["event_type"],
        amount=payload["amount"],
        currency=payload.get("currency", "USD"),
        plan_name=payload.get("plan_name", ""),
        plan_interval=payload.get("plan_interval", ""),
        payment_method=payload.get("payment_method", ""),
        stripe_invoice_id=payload.get("stripe_invoice_id", ""),
        stripe_customer_id=payload.get("stripe_customer_id", ""),
        metadata=payload.get("metadata", {}),
        timestamp=payload.get("timestamp", time.time()),
    )
    advanced_analytics.track_revenue(event)
    return {"status": "OK"}


@router.get("/revenue")
async def get_revenue_analytics(authorization: str = Header(None), days: int = 30, user_id: Optional[str] = None):
    """Get revenue analytics."""
    get_user_id_from_token(authorization)
    data = advanced_analytics.get_revenue_analytics(days=days, user_id=user_id)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# 15. Custom report builder
# ------------------------------------------------------------------
@router.post("/reports")
async def create_report(authorization: str = Header(None), payload: dict = Body(...)):
    """Create a custom report."""
    user_id = get_user_id_from_token(authorization)
    from app.analytics.advanced import CustomReport
    report = CustomReport(
        report_id=payload.get("report_id", str(uuid.uuid4())),
        report_name=payload["report_name"],
        description=payload.get("description", ""),
        created_by=user_id,
        config=payload["config"],
        schedule=payload.get("schedule", ""),
        recipients=payload.get("recipients", []),
        is_public=payload.get("is_public", False),
    )
    advanced_analytics.create_custom_report(report)
    return {"status": "OK", "report_id": report.report_id}


@router.post("/reports/{report_id}/run")
async def run_report(report_id: str, authorization: str = Header(None), days: int = 30):
    """Run a custom report."""
    get_user_id_from_token(authorization)
    result = advanced_analytics.run_custom_report(report_id=report_id, days=days)
    return {"status": "OK", "data": result}


# ------------------------------------------------------------------
# AI usage (legacy compatibility)
# ------------------------------------------------------------------
@router.get("/ai-usage")
async def get_ai_usage(authorization: str = Header(None), days: int = 7):
    """Get AI usage analytics."""
    user_id = get_user_id_from_token(authorization)
    data = advanced_analytics.get_usage_stats(days=days)
    return {"status": "OK", "data": data}


# ------------------------------------------------------------------
# Search analytics (legacy)
# ------------------------------------------------------------------
@router.get("/search")
async def get_search_analytics(authorization: str = Header(None), days: int = 7):
    """Get search quality metrics."""
    user_id = get_user_id_from_token(authorization)
    cutoff = time.time() - (days * 86400)
    events = [e for e in advanced_analytics._events if e.timestamp >= cutoff and e.event_type == "search"]
    total = len(events)
    return {
        "status": "OK",
        "data": {
            "period_days": days,
            "total_queries": total,
            "top_queries": [],
        }
    }


# ------------------------------------------------------------------
# Knowledge analytics (legacy)
# ------------------------------------------------------------------
@router.get("/knowledge")
async def get_knowledge_analytics(authorization: str = Header(None), days: int = 7):
    """Get knowledge growth metrics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "data": {"period_days": days, "documents_indexed": 0, "entities_extracted": 0}}


# ------------------------------------------------------------------
# Workflow analytics (legacy)
# ------------------------------------------------------------------
@router.get("/workflows")
async def get_workflow_analytics(authorization: str = Header(None), days: int = 7):
    """Get workflow statistics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "data": {"period_days": days, "total_executions": 0, "success_rate": 0}}


# ------------------------------------------------------------------
# Agent analytics (legacy)
# ------------------------------------------------------------------
@router.get("/agents")
async def get_agent_analytics(authorization: str = Header(None), days: int = 7):
    """Get agent performance metrics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "data": {"period_days": days, "total_tasks": 0, "success_rate": 0}}


# ------------------------------------------------------------------
# Users analytics (legacy)
# ------------------------------------------------------------------
@router.get("/users")
async def get_user_analytics(authorization: str = Header(None), days: int = 7):
    """Get user activity metrics."""
    user_id = get_user_id_from_token(authorization)
    return {"status": "OK", "data": {"period_days": days, "active_users": 0, "total_actions": 0}}


# ------------------------------------------------------------------
# Export
# ------------------------------------------------------------------
@router.get("/export")
async def export_analytics(authorization: str = Header(None), days: int = 30, format: str = "json"):
    """Export analytics data."""
    user_id = get_user_id_from_token(authorization)
    data = analytics.export_analytics(days=days, format=format)
    return {"status": "OK", "data": data}
