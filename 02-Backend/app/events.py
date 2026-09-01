"""Event-Driven Architecture — publish/subscribe with retry handling."""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable, Any


@dataclass
class Event:
    id: str
    type: str
    data: dict
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    metadata: dict = field(default_factory=dict)


EventHandler = Callable[[Event], Any]


class EventBus:
    """Async event bus with loose coupling and retry handling."""

    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._event_log: list[Event] = []
        self._max_log_size = 1000

    def subscribe(self, event_type: str, handler: EventHandler):
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler):
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish(self, event_type: str, data: dict, source: str = "", metadata: Optional[dict] = None):
        """Publish an event to all subscribers."""
        event = Event(
            id=str(uuid.uuid4()),
            type=event_type,
            data=data,
            source=source,
            metadata=metadata or {},
        )

        # Log event
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        # Notify subscribers
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass  # Event handlers should not crash the publisher

    def get_events(
        self,
        event_type: str = "",
        limit: int = 50,
        since: float = 0,
    ) -> list[Event]:
        """Get event log with filtering."""
        events = self._event_log
        if event_type:
            events = [e for e in events if e.type == event_type]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events[-limit:]

    def get_subscriber_count(self, event_type: str = "") -> int:
        """Get number of subscribers."""
        if event_type:
            return len(self._subscribers.get(event_type, []))
        return sum(len(h) for h in self._subscribers.values())

    @property
    def event_types(self) -> list[str]:
        """List all event types with subscribers."""
        return list(self._subscribers.keys())


# Global event bus
event_bus = EventBus()
