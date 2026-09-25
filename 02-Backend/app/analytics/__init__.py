
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


class _AnalyticsClient:
    def track_user_action(self, user_id, action, metadata):
        record_event(user_id, action, metadata)

    def track_user_session(self, user_id, event_name, category):
        record_event(user_id, event_name, {"category": category})

    def track_error(self, user_id, error_name, error_message):
        record_event(user_id, f"error:{error_name}", {"message": error_message})


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
    "analytics",
]
