"""
User behavior analysis for AstrovoxAI.
Analyzes user journeys, feature adoption, and engagement patterns.
"""

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BehaviorEventType(str, Enum):
    PAGE_VIEW = "page_view"
    FEATURE_USED = "feature_used"
    API_CALL = "api_call"
    ERROR = "error"
    CONVERSION = "conversion"


@dataclass
class BehaviorEvent:
    event_id: str
    developer_id: str
    event_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "developer_id": self.developer_id,
            "event_type": self.event_type,
            "properties": self.properties,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class UserJourney:
    journey_id: str
    developer_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed: bool = False

    def add_step(self, event: BehaviorEvent) -> None:
        self.steps.append({
            "event_id": event.event_id,
            "event_type": event.event_type,
            "properties": event.properties,
            "timestamp": event.timestamp.isoformat(),
        })


class UserBehaviorAnalyzer:
    """Analyzes user behavior and engagement patterns."""

    def __init__(self):
        self._events: List[BehaviorEvent] = []
        self._journeys: Dict[str, UserJourney] = {}

    def track_event(
        self,
        developer_id: str,
        event_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> BehaviorEvent:
        event = BehaviorEvent(
            event_id=str(uuid.uuid4()),
            developer_id=developer_id,
            event_type=event_type,
            properties=properties or {},
        )
        self._events.append(event)
        return event

    def get_feature_adoption(self, feature: str, days: int = 30) -> Dict[str, Any]:
        start = datetime.utcnow() - timedelta(days=days)
        events = [
            e for e in self._events
            if e.event_type == "feature_used"
            and e.properties.get("feature") == feature
            and e.timestamp >= start
        ]
        unique_users = len({e.developer_id for e in events})
        return {
            "feature": feature,
            "total_events": len(events),
            "unique_users": unique_users,
            "period_days": days,
        }

    def get_user_retention(self, cohort_start: datetime, days: int = 30) -> Dict[str, Any]:
        cohort_users = {
            e.developer_id for e in self._events
            if e.timestamp >= cohort_start
            and e.timestamp < cohort_start + timedelta(days=7)
        }
        retained = {
            uid for uid in cohort_users
            if any(
                e.developer_id == uid
                and e.timestamp >= cohort_start + timedelta(days=days)
                for e in self._events
            )
        }
        return {
            "cohort_start": cohort_start.isoformat(),
            "cohort_size": len(cohort_users),
            "retained_count": len(retained),
            "retention_rate": len(retained) / len(cohort_users) if cohort_users else 0.0,
        }

    def get_top_features(self, days: int = 7) -> List[Dict[str, Any]]:
        start = datetime.utcnow() - timedelta(days=days)
        feature_counts: Dict[str, int] = defaultdict(int)
        for e in self._events:
            if e.timestamp >= start and e.event_type == "feature_used":
                feature = e.properties.get("feature", "unknown")
                feature_counts[feature] += 1
        return [
            {"feature": k, "count": v}
            for k, v in sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)
        ]

    def start_journey(self, developer_id: str) -> UserJourney:
        journey = UserJourney(journey_id=str(uuid.uuid4()), developer_id=developer_id)
        self._journeys[journey.journey_id] = journey
        return journey
