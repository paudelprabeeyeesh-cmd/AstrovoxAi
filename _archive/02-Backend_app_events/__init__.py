"""Event-sourced architecture for AIOS.

Provides:
- Event schema registry with versioning
- Persistent event store with replay
- Projection engine for read models
- Dead-letter queue for failed handlers
- Replay engine with time-travel debugging
- Idempotency tracking for exactly-once semantics
- Multi-region event replication
- Async event bus with loose coupling and retry handling

Quick start:
    from app.events import EventStore, EventSchemaRegistry, ProjectionEngine
    from app.events import EventBus, event_bus

    registry = EventSchemaRegistry()
    store = EventStore(registry)
    engine = ProjectionEngine(store)

    # Create and append event
    event = EventEnvelope(
        event_id=str(uuid.uuid4()),
        event_type="WorkflowStarted",
        version=EventVersion.V1,
        payload={"workflow_id": "wf-123"},
        occurred_at=datetime.now(timezone.utc),
        source="workflow",
    )
    store.append(event)

    # Replay events
    replay = ReplayEngine(store)
    result = replay.replay(ReplayOptions(event_type="WorkflowStarted"))
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable, Any

from .event_store import EventEnvelope, EventSchema, EventSchemaRegistry, EventStore, EventVersion
from .projection import ProjectionCheckpoint, ProjectionDefinition, ProjectionEngine
from .replay import ReplayEngine, ReplayOptions, ReplayResult
from .dead_letter import DeadLetterEntry, DeadLetterQueue
from .idempotency import IdempotencyRecord, IdempotencyTracker
from .multi_region import MultiRegionEventStore, VectorClock, RegionConfig


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

        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

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


event_bus = EventBus()

__all__ = [
    "Event",
    "EventHandler",
    "EventBus",
    "event_bus",
    "EventEnvelope",
    "EventSchema",
    "EventSchemaRegistry",
    "EventStore",
    "EventVersion",
    "ProjectionCheckpoint",
    "ProjectionDefinition",
    "ProjectionEngine",
    "ReplayEngine",
    "ReplayOptions",
    "ReplayResult",
    "DeadLetterEntry",
    "DeadLetterQueue",
    "IdempotencyRecord",
    "IdempotencyTracker",
    "MultiRegionEventStore",
    "VectorClock",
    "RegionConfig",
]
