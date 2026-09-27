"""
Usage tracking for AstrovoxAI.
Records API calls, model usage, and resource consumption for billing.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UsageEventType(str, Enum):
    API_CALL = "api_call"
    MODEL_INFERENCE = "model_inference"
    TOKEN_USAGE = "token_usage"
    STORAGE = "storage"
    COMPUTE = "compute"


class UsageUnit(str, Enum):
    CALL = "call"
    TOKEN = "token"
    REQUEST = "request"
    GB = "gb"
    HOUR = "hour"


@dataclass
class UsageEvent:
    event_id: str
    developer_id: str
    project_id: Optional[str]
    event_type: UsageEventType
    unit: UsageUnit
    quantity: float
    model_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "developer_id": self.developer_id,
            "project_id": self.project_id,
            "event_type": self.event_type.value,
            "unit": self.unit.value,
            "quantity": self.quantity,
            "model_id": self.model_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class UsageSummary:
    developer_id: str
    period_start: datetime
    period_end: datetime
    total_events: int
    total_quantity: float
    estimated_cost: float
    breakdown: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "developer_id": self.developer_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_events": self.total_events,
            "total_quantity": self.total_quantity,
            "estimated_cost": self.estimated_cost,
            "breakdown": self.breakdown,
        }


class UsageTracker:
    """Tracks API usage for billing purposes."""

    def __init__(self, storage_backend: Optional[Any] = None):
        self._storage = storage_backend
        self._events: List[UsageEvent] = []
        self._rate_limits: Dict[str, Dict[str, Any]] = {}

    def record_event(
        self,
        developer_id: str,
        event_type: UsageEventType,
        unit: UsageUnit,
        quantity: float = 1.0,
        project_id: Optional[str] = None,
        model_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageEvent:
        event = UsageEvent(
            event_id=str(uuid.uuid4()),
            developer_id=developer_id,
            project_id=project_id,
            event_type=event_type,
            unit=unit,
            quantity=quantity,
            model_id=model_id,
            metadata=metadata or {},
        )
        self._events.append(event)
        logger.debug("Recorded usage event: %s", event.event_id)
        return event

    def get_usage_summary(
        self,
        developer_id: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> UsageSummary:
        start = start or datetime.utcnow() - timedelta(days=30)
        end = end or datetime.utcnow()
        events = [
            e for e in self._events
            if e.developer_id == developer_id and start <= e.timestamp <= end
        ]
        total_quantity = sum(e.quantity for e in events)
        breakdown: Dict[str, float] = {}
        for e in events:
            key = f"{e.event_type.value}:{e.unit.value}"
            breakdown[key] = breakdown.get(key, 0.0) + e.quantity
        estimated_cost = self._estimate_cost(events)
        return UsageSummary(
            developer_id=developer_id,
            period_start=start,
            period_end=end,
            total_events=len(events),
            total_quantity=total_quantity,
            estimated_cost=estimated_cost,
            breakdown=breakdown,
        )

    def _estimate_cost(self, events: List[UsageEvent]) -> float:
        cost = 0.0
        for event in events:
            if event.event_type == UsageEventType.TOKEN_USAGE:
                cost += event.quantity * 0.00002
            elif event.event_type == UsageEventType.API_CALL:
                cost += 0.001
            elif event.event_type == UsageEventType.MODEL_INFERENCE:
                cost += 0.005
            elif event.event_type == UsageEventType.STORAGE:
                cost += event.quantity * 0.023
            elif event.event_type == UsageEventType.COMPUTE:
                cost += event.quantity * 0.0001
        return round(cost, 4)

    def check_rate_limit(
        self,
        developer_id: str,
        limit_type: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> bool:
        now = time.time()
        key = f"{developer_id}:{limit_type}"
        window_start = now - window_seconds
        if key not in self._rate_limits:
            self._rate_limits[key] = {"timestamps": [], "max": max_requests, "window": window_seconds}
        self._rate_limits[key]["timestamps"] = [
            ts for ts in self._rate_limits[key]["timestamps"] if ts > window_start
        ]
        current_count = len(self._rate_limits[key]["timestamps"])
        if current_count >= max_requests:
            logger.warning("Rate limit exceeded for %s on %s", developer_id, limit_type)
            return False
        self._rate_limits[key]["timestamps"].append(now)
        return True
