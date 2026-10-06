"""Analytics pipeline for Astrovox usage data."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    """A usage event."""
    user_id: str
    event: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


class AnalyticsPipeline:
    """Collect and analyze usage events."""

    def __init__(self):
        self.events: list[Event] = []
        self.counters: dict[str, int] = {}

    def record(self, user_id: str, event: str, **metadata) -> None:
        self.events.append(Event(user_id=user_id, event=event, metadata=metadata))
        key = f"{user_id}:{event}"
        self.counters[key] = self.counters.get(key, 0) + 1

    def count(self, event: str | None = None) -> int:
        if event is None:
            return len(self.events)
        return sum(1 for e in self.events if e.event == event)

    def by_user(self, user_id: str, event: str | None = None) -> int:
        return sum(1 for e in self.events if e.user_id == user_id and (event is None or e.event == event))

    def summary(self) -> dict:
        return {"total_events": len(self.events), "unique_users": len({e.user_id for e in self.events}),
                "event_counts": {e: self.count(e) for e in set(x.event for x in self.events)}}

    def reset(self) -> None:
        self.events.clear()
        self.counters.clear()
