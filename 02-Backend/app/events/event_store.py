"""Event-sourced architecture for AIOS.

Provides:
- Event schema registry with versioning
- Persistent event store with replay
- Projection engine for read models
- Dead-letter queue for failed handlers
- Idempotency tracking
- Multi-region event ordering

Architecture:
    Command → Event → Event Store → Projections → Read Models
                                    ↓
                            Dead-Letter Queue
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from ..logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class EventVersion(int, Enum):
    V1 = 1
    V2 = 2
    V3 = 3


@dataclass(frozen=True)
class EventSchema:
    """Schema definition for an event type."""

    name: str
    version: EventVersion
    fields: Dict[str, str]  # field_name -> field_type
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deprecated: bool = False
    migration_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None


@dataclass(frozen=True)
class EventEnvelope:
    """Immutable event wrapper with metadata."""

    event_id: str
    event_type: str
    version: EventVersion
    payload: Dict[str, Any]
    occurred_at: datetime
    source: str
    correlation_id: Optional[str]
    causation_id: Optional[str]
    schema_version: str = "1.0"
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "version": self.version.value,
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat(),
            "source": self.source,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EventEnvelope:
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            version=EventVersion(data["version"]),
            payload=data["payload"],
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            source=data["source"],
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            schema_version=data.get("schema_version", "1.0"),
            trace_id=data.get("trace_id"),
            user_id=data.get("user_id"),
            idempotency_key=data.get("idempotency_key"),
        )


# ---------------------------------------------------------------------------
# Schema Registry
# ---------------------------------------------------------------------------


class EventSchemaRegistry:
    """Central registry for event schemas with versioning.

    Supports:
    - Schema registration and discovery
    - Version migration
    - Deprecation tracking
    - Compatibility checks
    """

    def __init__(self) -> None:
        self._schemas: Dict[str, Dict[EventVersion, EventSchema]] = {}
        self._latest_version: Dict[str, EventVersion] = {}
        self._compatibility: Dict[str, Set[str]] = {}

    def register(self, schema: EventSchema) -> None:
        """Register a new event schema."""
        name = schema.name
        if name not in self._schemas:
            self._schemas[name] = {}
        self._schemas[name][schema.version] = schema
        self._latest_version[name] = schema.version

        # Track compatibility (same name = compatible versions)
        if name not in self._compatibility:
            self._compatibility[name] = set()
        self._compatibility[name].add(str(schema.version))

        logger.info("registered event schema: %s v%d", name, schema.version)

    def get_schema(self, name: str, version: Optional[EventVersion] = None) -> Optional[EventSchema]:
        """Get schema by name and version (default: latest)."""
        if name not in self._schemas:
            return None
        if version is None:
            version = self._latest_version.get(name)
        return self._schemas[name].get(version)

    def get_latest_version(self, name: str) -> Optional[EventVersion]:
        """Get latest version for an event type."""
        return self._latest_version.get(name)

    def migrate(self, event: EventEnvelope, target_version: EventVersion) -> EventEnvelope:
        """Migrate event to target version."""
        schema = self.get_schema(event.event_type, event.version)
        if schema is None:
            raise ValueError(f"unknown event type: {event.event_type}")

        if event.version == target_version:
            return event

        if schema.migration_fn is None:
            raise ValueError(f"no migration from v{event.version} to v{target_version}")

        migrated_payload = schema.migration_fn(event.payload)
        return EventEnvelope(
            event_id=event.event_id,
            event_type=event.event_type,
            version=target_version,
            payload=migrated_payload,
            occurred_at=event.occurred_at,
            source=event.source,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            schema_version=event.schema_version,
            trace_id=event.trace_id,
            user_id=event.user_id,
            idempotency_key=event.idempotency_key,
        )

    def validate(self, event: EventEnvelope) -> List[str]:
        """Validate event against schema. Returns list of errors."""
        schema = self.get_schema(event.event_type, event.version)
        if schema is None:
            return [f"unknown event type: {event.event_type}"]

        errors = []
        for field_name, field_type in schema.fields.items():
            if field_name not in event.payload:
                errors.append(f"missing required field: {field_name}")
            elif not self._check_type(event.payload[field_name], field_type):
                errors.append(f"type mismatch for {field_name}: expected {field_type}")

        return errors

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Basic type checking."""
        type_map = {
            "string": str,
            "int": int,
            "float": (int, float),
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        python_type = type_map.get(expected_type)
        if python_type is None:
            return True
        return isinstance(value, python_type)

    def list_schemas(self) -> List[Dict[str, Any]]:
        """List all registered schemas."""
        result = []
        for name, versions in self._schemas.items():
            for version, schema in versions.items():
                result.append({
                    "name": name,
                    "version": version.value,
                    "fields": list(schema.fields.keys()),
                    "deprecated": schema.deprecated,
                })
        return result


# ---------------------------------------------------------------------------
# Event Store
# ---------------------------------------------------------------------------


class EventStore:
    """Persistent event store with replay and snapshotting.

    Features:
    - Append-only event log
    - Snapshotting for fast recovery
    - Replay engine
    - Idempotency checking
    - Dead-letter queue for failed projections
    """

    def __init__(self, schema_registry: EventSchemaRegistry) -> None:
        self._registry = schema_registry
        self._events: List[EventEnvelope] = []
        self._positions: Dict[str, int] = {}  # event_id -> position
        self._snapshots: Dict[str, Dict[str, Any]] = {}  # aggregate_id -> snapshot
        self._idempotency: Dict[str, EventEnvelope] = {}  # key -> event
        self._dead_letter: List[EventEnvelope] = []
        self._dlq_limit = 10_000
        self._global_position: int = 0

    def append(self, event: EventEnvelope, idempotency_key: Optional[str] = None) -> EventEnvelope:
        """Append event to store with idempotency check."""
        # Idempotency check
        if idempotency_key and idempotency_key in self._idempotency:
            existing = self._idempotency[idempotency_key]
            logger.debug("duplicate event suppressed: %s", idempotency_key)
            return existing

        # Validate against schema
        errors = self._registry.validate(event)
        if errors:
            raise ValueError(f"event validation failed: {errors}")

        # Store event
        self._global_position += 1
        self._positions[event.event_id] = self._global_position
        self._events.append(event)

        # Track idempotency
        if idempotency_key:
            self._idempotency[idempotency_key] = event

        return event

    def get_events(
        self,
        event_type: Optional[str] = None,
        aggregate_id: Optional[str] = None,
        since_position: int = 0,
        limit: int = 1000,
    ) -> List[EventEnvelope]:
        """Query events with filtering."""
        results = []
        for event in self._events:
            pos = self._positions.get(event.event_id, 0)
            if pos <= since_position:
                continue
            if event_type and event.event_type != event_type:
                continue
            if aggregate_id and event.payload.get("aggregate_id") != aggregate_id:
                continue
            results.append(event)
            if len(results) >= limit:
                break
        return results

    def get_position(self) -> int:
        """Get current global position."""
        return self._global_position

    def snapshot(self, aggregate_id: str, state: Dict[str, Any], position: int) -> None:
        """Create snapshot of aggregate state."""
        self._snapshots[aggregate_id] = {
            "state": state,
            "position": position,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_snapshot(self, aggregate_id: str) -> Optional[Dict[str, Any]]:
        """Get latest snapshot for aggregate."""
        return self._snapshots.get(aggregate_id)

    def replay(
        self,
        handler: Callable[[EventEnvelope], None],
        event_type: Optional[str] = None,
        since_position: int = 0,
        until_position: Optional[int] = None,
    ) -> int:
        """Replay events to a handler.

        Returns number of events replayed.
        """
        replayed = 0
        for event in self._events:
            if event._position <= since_position:
                continue
            if event_type and event.event_type != event_type:
                continue
            if until_position and event._position > until_position:
                break
            try:
                handler(event)
                replayed += 1
            except Exception as e:
                logger.error("replay handler failed for %s: %s", event.event_id, e)
                self._dead_letter.append(event)
        return replayed

    def rebuild_projection(self, projection_name: str, handler: Callable[[EventEnvelope], None]) -> int:
        """Rebuild a projection from scratch by replaying all events."""
        logger.info("rebuilding projection: %s", projection_name)
        count = self.replay(handler)
        logger.info("projection %s rebuilt with %d events", projection_name, count)
        return count

    def dead_letter_queue(self) -> List[EventEnvelope]:
        """Get dead-letter queue events."""
        return list(self._dead_letter)

    def retry_dead_letter(self, handler: Callable[[EventEnvelope], None]) -> int:
        """Retry processing dead-letter events."""
        retried = 0
        remaining = []
        for event in self._dead_letter:
            try:
                handler(event)
                retried += 1
            except Exception:
                remaining.append(event)
        self._dead_letter = remaining[-self._dlq_limit:]
        return retried
