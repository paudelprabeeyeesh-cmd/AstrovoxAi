"""Analytics dashboard — track application usage and performance."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from .shared import MODEL_COSTS

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsEvent:
    """A single analytics event."""
    event_type: str
    user_id: str
    timestamp: float
    metadata: dict = field(default_factory=dict)


@dataclass
class UsageStats:
    """Aggregated usage statistics."""
    total_requests: int = 0
    total_tokens: int = 0
    total_errors: int = 0
    total_latency: float = 0.0
    average_latency: float = 0.0
    error_rate: float = 0.0
    requests_per_provider: dict = field(default_factory=dict)
    requests_per_model: dict = field(default_factory=dict)
    requests_per_day: dict = field(default_factory=dict)
    active_users: int = 0
    total_users: int = 0


class AnalyticsTracker:
    """Track and aggregate application analytics."""

    def __init__(self):
        self._events: list[AnalyticsEvent] = []
        self._user_activity: dict[str, float] = {}
        self._daily_requests: dict[str, int] = defaultdict(int)
        self._provider_requests: dict[str, int] = defaultdict(int)
        self._model_requests: dict[str, int] = defaultdict(int)
        self._error_count: int = 0
        self._total_latency: float = 0.0
        self._total_tokens: int = 0

    def track_request(
        self,
        user_id: str,
        model: str,
        provider: str,
        tokens: int = 0,
        latency: float = 0.0,
        success: bool = True,
    ):
        """Track an AI request."""
        now = time.time()
        event = AnalyticsEvent(
            event_type="ai_request",
            user_id=user_id,
            timestamp=now,
            metadata={
                "model": model,
                "provider": provider,
                "tokens": tokens,
                "latency": latency,
                "success": success,
            },
        )
        self._events.append(event)
        self._user_activity[user_id] = now

        day_key = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        self._daily_requests[day_key] += 1
        self._provider_requests[provider] += 1
        self._model_requests[model] += 1
        self._total_tokens += tokens
        self._total_latency += latency

        if not success:
            self._error_count += 1

    def track_error(self, user_id: str, error_type: str, details: str = ""):
        """Track an error event."""
        event = AnalyticsEvent(
            event_type="error",
            user_id=user_id,
            timestamp=time.time(),
            metadata={"error_type": error_type, "details": details},
        )
        self._events.append(event)
        self._error_count += 1

    def track_user_action(self, user_id: str, action: str, metadata: dict = None):
        """Track a user action."""
        event = AnalyticsEvent(
            event_type="user_action",
            user_id=user_id,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        self._events.append(event)
        self._user_activity[user_id] = time.time()

    def get_usage_stats(self, days: int = 7) -> UsageStats:
        """Get aggregated usage statistics."""
        cutoff = time.time() - (days * 86400)
        recent_events = [e for e in self._events if e.timestamp >= cutoff]

        total_requests = len([e for e in recent_events if e.event_type == "ai_request"])
        error_count = len([e for e in recent_events if e.event_type == "error"])

        total_tokens = sum(
            e.metadata.get("tokens", 0)
            for e in recent_events
            if e.event_type == "ai_request"
        )
        total_latency = sum(
            e.metadata.get("latency", 0.0)
            for e in recent_events
            if e.event_type == "ai_request"
        )

        active_users = len([
            uid for uid, last_seen in self._user_activity.items()
            if last_seen >= cutoff
        ])

        return UsageStats(
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_errors=error_count,
            total_latency=total_latency,
            average_latency=total_latency / total_requests if total_requests > 0 else 0,
            error_rate=error_count / total_requests if total_requests > 0 else 0,
            requests_per_provider=dict(self._provider_requests),
            requests_per_model=dict(self._model_requests),
            requests_per_day=dict(self._daily_requests),
            active_users=active_users,
            total_users=len(self._user_activity),
        )

    def get_provider_breakdown(self) -> dict:
        """Get usage breakdown by provider."""
        return dict(self._provider_requests)

    def get_model_breakdown(self) -> dict:
        """Get usage breakdown by model."""
        return dict(self._model_requests)

    def get_daily_usage(self, days: int = 30) -> dict:
        """Get daily request counts."""
        result = {}
        today = datetime.now()
        for i in range(days):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            result[day] = self._daily_requests.get(day, 0)
        return result

    def get_cost_estimate(self) -> dict:
        """Estimate costs based on usage."""
        costs = {}
        for model, count in self._model_requests.items():
            if model in MODEL_COSTS:
                cost = MODEL_COSTS[model]
                estimated = (cost["input"] + cost["output"]) * count
                costs[model] = round(estimated, 4)
        return costs

    def get_dashboard_data(self) -> dict:
        """Get all dashboard data."""
        stats = self.get_usage_stats()
        return {
            "total_requests": stats.total_requests,
            "total_tokens": stats.total_tokens,
            "average_latency": round(stats.average_latency, 3),
            "error_rate": round(stats.error_rate, 4),
            "active_users": stats.active_users,
            "total_users": stats.total_users,
            "provider_breakdown": self.get_provider_breakdown(),
            "model_breakdown": self.get_model_breakdown(),
            "daily_usage": self.get_daily_usage(),
            "cost_estimate": self.get_cost_estimate(),
        }


# Singleton instance

analytics = AnalyticsTracker()
