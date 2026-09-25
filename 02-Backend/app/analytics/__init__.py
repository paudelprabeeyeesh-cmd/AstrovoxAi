from .enhanced import (
    get_organization_analytics,
    get_workspace_analytics,
    get_user_analytics,
    export_analytics_csv,
    export_analytics_json,
    get_realtime_dashboard,
)
from .core import (
    record_event,
    track_event,
    get_aggregate_metrics,
    get_top_models,
    get_cost_trend,
)
from .advanced import AdvancedAnalyticsEngine

AdvancedAnalyticsEngine = AdvancedAnalyticsEngine
AnalyticsEngine = AdvancedAnalyticsEngine

advanced_analytics = AdvancedAnalyticsEngine()


class _AnalyticsClient:
    def track_user_action(self, user_id, action, metadata):
        advanced_analytics.track_user_action(user_id, action, metadata)

    def track_user_session(self, user_id, event_name, category):
        advanced_analytics.track_user_action(user_id, event_name, {"category": category})

    def track_error(self, user_id, error_name, error_message):
        advanced_analytics.track_error(user_id, error_name, error_message)

    def track_request(self, user_id, model, provider, tokens=0, latency=0.0, success=True, session_id="", page_url="", duration_ms=0):
        advanced_analytics.track_request(user_id, model, provider, tokens, latency, success, session_id, page_url, duration_ms)

    def track_feature_use(self, user_id, feature_name, category="general"):
        advanced_analytics.track_feature_use(user_id, feature_name, category)

    def track_behavior(self, behavior_event):
        advanced_analytics.track_behavior(behavior_event)

    def track_conversation(self, conv):
        advanced_analytics.track_conversation(conv)

    def track_revenue(self, revenue_event):
        advanced_analytics.track_revenue(revenue_event)

    def create_ab_test(self, test):
        advanced_analytics.create_ab_test(test)

    def assign_ab_test(self, assignment):
        advanced_analytics.assign_ab_test(assignment)

    def track_ab_event(self, event):
        advanced_analytics.track_ab_event(event)

    def create_funnel(self, funnel):
        advanced_analytics.create_funnel(funnel)

    def track_funnel_event(self, event):
        advanced_analytics.track_funnel_event(event)

    def create_cohort(self, cohort):
        advanced_analytics.create_cohort(cohort)

    def add_cohort_member(self, member):
        advanced_analytics.add_cohort_member(member)

    def update_retention_snapshot(self, snapshot):
        advanced_analytics.update_retention_snapshot(snapshot)

    def create_custom_report(self, report):
        advanced_analytics.create_custom_report(report)

    def get_dashboard_data(self, days=7):
        return advanced_analytics.get_dashboard_data(days=days)

    def get_usage_stats(self, days=7):
        return advanced_analytics.get_usage_stats(days=days)

    def get_token_analytics(self, days=7):
        return advanced_analytics.get_token_analytics(days=days)

    def get_cost_analytics(self, days=7):
        return advanced_analytics.get_cost_analytics(days=days)

    def get_performance_analytics(self, days=7):
        return advanced_analytics.get_performance_analytics(days=days)

    def get_error_analytics(self, days=7):
        return advanced_analytics.get_error_analytics(days=days)

    def get_feature_adoption_analytics(self, days=30):
        return advanced_analytics.get_feature_adoption_analytics(days=days)

    def get_conversation_analytics(self, days=7):
        return advanced_analytics.get_conversation_analytics(days=days)

    def get_model_performance(self, days=7):
        return advanced_analytics.get_model_performance_comparison(days=days)

    def get_ab_test_analytics(self, test_id):
        return advanced_analytics.get_ab_test_analytics(test_id=test_id)

    def get_cohort_analysis(self, cohort_id, days=30):
        return advanced_analytics.get_cohort_analysis(cohort_id=cohort_id, days=days)

    def get_funnel_analytics(self, funnel_id, days=30):
        return advanced_analytics.get_funnel_analytics(funnel_id=funnel_id, days=days)

    def get_retention_analytics(self, cohort_date, days=90):
        return advanced_analytics.get_retention_analytics(cohort_date=cohort_date, days=days)

    def get_revenue_analytics(self, days=30):
        return advanced_analytics.get_revenue_analytics(days=days)

    def run_custom_report(self, report_id, days=30):
        return advanced_analytics.run_custom_report(report_id=report_id, days=days)

    def export_analytics(self, days=30, format="json"):
        return advanced_analytics.export_analytics(days=days, format=format)

    def get_provider_breakdown(self):
        return advanced_analytics.get_provider_breakdown()

    def get_model_breakdown(self):
        return advanced_analytics.get_model_breakdown()

    def get_daily_usage(self, days=30):
        return advanced_analytics.get_daily_usage(days=days)

    def get_overview(self, days=7):
        return advanced_analytics.get_overview(days=days)

    def get_ai_usage_analytics(self, days=7):
        return advanced_analytics.get_ai_usage_analytics(days=days)

    def get_search_analytics(self, days=7):
        return advanced_analytics.get_search_analytics(days=days)

    def get_knowledge_analytics(self, days=7):
        return advanced_analytics.get_knowledge_analytics(days=days)

    def get_workflow_analytics(self, days=7):
        return advanced_analytics.get_workflow_analytics(days=days)

    def get_agent_analytics(self, days=7):
        return advanced_analytics.get_agent_analytics(days=days)

    def get_user_analytics(self, days=7):
        return advanced_analytics.get_user_analytics(days=days)


analytics = _AnalyticsClient()

__all__ = [
    "get_organization_analytics",
    "get_workspace_analytics",
    "get_user_analytics",
    "export_analytics_csv",
    "export_analytics_json",
    "get_realtime_dashboard",
    "record_event",
    "track_event",
    "get_aggregate_metrics",
    "get_top_models",
    "get_cost_trend",
    "AdvancedAnalyticsEngine",
    "advanced_analytics",
    "analytics",
]
