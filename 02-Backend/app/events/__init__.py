"""Event-sourced architecture for AIOS.

Provides:
- Event schema registry with versioning
- Persistent event store with replay
- Projection engine for read models
- Dead-letter queue for failed handlers
- Replay engine with time-travel debugging
- Idempotency tracking for exactly-once semantics
- Multi-region event replication

Quick start:
    from app.events import EventStore, EventSchemaRegistry, ProjectionEngine

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

from .event_store import EventEnvelope, EventSchema, EventSchemaRegistry, EventStore, EventVersion
from .projection import ProjectionCheckpoint, ProjectionDefinition, ProjectionEngine
from .replay import ReplayEngine, ReplayOptions, ReplayResult
from .dead_letter import DeadLetterEntry, DeadLetterQueue
from .idempotency import IdempotencyRecord, IdempotencyTracker
from .multi_region import MultiRegionEventStore, VectorClock, RegionConfig

__all__ = [
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
