from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ScheduledEvent:
    id: str
    time: float
    action: Callable[["ScheduledEvent"], None]
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False

    def __lt__(self, other: "ScheduledEvent") -> bool:
        return self.time < other.time


class EventScheduler:
    def __init__(self) -> None:
        self._queue: List[ScheduledEvent] = []
        self._events: Dict[str, ScheduledEvent] = {}
        self._current_time: float = 0.0

    def schedule(self, event_id: str, time: float, action: Callable[["ScheduledEvent"], None], *args: Any, **kwargs: Any) -> ScheduledEvent:
        if event_id in self._events:
            raise ValueError(f"Event already scheduled: {event_id}")
        event = ScheduledEvent(id=event_id, time=time, action=action, args=list(args), kwargs=dict(kwargs))
        heapq.heappush(self._queue, event)
        self._events[event_id] = event
        return event

    def cancel(self, event_id: str) -> None:
        event = self._events.pop(event_id, None)
        if event is not None:
            event.cancelled = True

    def step(self) -> List[ScheduledEvent]:
        fired: List[ScheduledEvent] = []
        while self._queue and self._queue[0].time <= self._current_time:
            event = heapq.heappop(self._queue)
            if event.cancelled:
                continue
            if event.id in self._events and self._events[event.id] is event:
                del self._events[event.id]
            try:
                event.action(event)
            finally:
                fired.append(event)
        return fired

    def advance(self, delta: float) -> List[ScheduledEvent]:
        self._current_time += delta
        return self.step()

    def set_time(self, time: float) -> None:
        self._current_time = time

    def pending(self) -> List[ScheduledEvent]:
        return [e for e in self._queue if not e.cancelled]

    def clear(self) -> None:
        self._queue.clear()
        self._events.clear()
        self._current_time = 0.0
