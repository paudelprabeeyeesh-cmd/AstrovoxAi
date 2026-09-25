"""Usage analytics collector for product insights, feature adoption, and user behavior."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class UsageEvent:
    event_id: str
    event_type: str
    user_id: Optional[str]
    session_id: str
    feature: str
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FeatureMetric:
    feature: str
    daily_active_users: int = 0
    weekly_active_users: int = 0
    monthly_active_users: int = 0
    total_events: int = 0
    avg_session_duration_seconds: float = 0.0


class UsageAnalyticsCollector:
    _events: List[UsageEvent] = []
    _features: Dict[str, FeatureMetric] = {}
    _lock = threading.RLock()
    _next_event_id = 1

    @classmethod
    def track_event(
        cls,
        event_type: str,
        feature: str,
        user_id: Optional[str] = None,
        session_id: str = "",
        properties: Optional[Dict[str, Any]] = None,
    ) -> UsageEvent:
        with cls._lock:
            event = UsageEvent(
                event_id=f"USG-{cls._next_event_id:06d}",
                event_type=event_type,
                user_id=user_id,
                session_id=session_id,
                feature=feature,
                properties=properties or {},
            )
            cls._events.append(event)
            cls._next_event_id += 1
            if len(cls._events) > 50000:
                cls._events = cls._events[-50000:]
            if feature not in cls._features:
                cls._features[feature] = FeatureMetric(feature=feature)
            fm = cls._features[feature]
            fm.total_events += 1
            return event

    @classmethod
    def get_feature_adoption(cls, window_days: int = 30) -> Dict[str, Dict[str, Any]]:
        with cls._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
            recent = [e for e in cls._events if e.timestamp >= cutoff]
        features: Dict[str, Any] = {}
        for e in recent:
            if e.feature not in features:
                features[e.feature] = {
                    "unique_users": set(),
                    "total_events": 0,
                    "events_by_type": {},
                }
            f = features[e.feature]
            f["total_events"] += 1
            if e.user_id:
                f["unique_users"].add(e.user_id)
            f["events_by_type"][e.event_type] = f["events_by_type"].get(e.event_type, 0) + 1
        return {
            k: {
                "unique_users": len(v["unique_users"]),
                "total_events": v["total_events"],
                "events_by_type": v["events_by_type"],
            }
            for k, v in features.items()
        }

    @classmethod
    def get_user_retention(cls, window_days: int = 30) -> Dict[str, Any]:
        with cls._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
            recent = [e for e in cls._events if e.timestamp >= cutoff]
        users_by_day: Dict[str, set] = {}
        for e in recent:
            day = e.timestamp.strftime("%Y-%m-%d")
            users_by_day.setdefault(day, set())
            if e.user_id:
                users_by_day[day].add(e.user_id)
        return {
            day: len(users) for day, users in sorted(users_by_day.items())
        }

    @classmethod
    def get_top_features(cls, limit: int = 10, window_days: int = 30) -> List[Dict[str, Any]]:
        adoption = cls.get_feature_adoption(window_days=window_days)
        return sorted(
            [{"feature": k, **v} for k, v in adoption.items()],
            key=lambda x: x["total_events"],
            reverse=True,
        )[:limit]

    @classmethod
    def get_session_analytics(cls, window_hours: int = 24) -> Dict[str, Any]:
        with cls._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            recent = [e for e in cls._events if e.timestamp >= cutoff]
        sessions: Dict[str, List[UsageEvent]] = {}
        for e in recent:
            sessions.setdefault(e.session_id, []).append(e)
        session_durations = []
        for sid, events in sessions.items():
            if len(events) > 1:
                first = min(e.timestamp for e in events)
                last = max(e.timestamp for e in events)
                session_durations.append((last - first).total_seconds())
        avg_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        return {
            "window_hours": window_hours,
            "total_sessions": len(sessions),
            "avg_duration_seconds": avg_duration,
            "total_events": len(recent),
        }

    @classmethod
    def get_dashboard_data(cls, window_hours: int = 24) -> Dict[str, Any]:
        return {
            "feature_adoption": cls.get_feature_adoption(),
            "top_features": cls.get_top_features(),
            "user_retention": cls.get_user_retention(),
            "session_analytics": cls.get_session_analytics(window_hours=window_hours),
        }


usage_analytics = UsageAnalyticsCollector()
