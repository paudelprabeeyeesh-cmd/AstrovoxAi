"""Analytics and metrics collection for the developer portal."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class UsageEvent:
    event_type: str
    user_id: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, str] = field(default_factory=dict)


class AnalyticsCollector:
    def __init__(self) -> None:
        self._events: List[UsageEvent] = []

    def track(self, event_type: str, user_id: str, **metadata: str) -> None:
        self._events.append(UsageEvent(event_type=event_type, user_id=user_id, metadata=metadata))

    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for event in self._events:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return counts
