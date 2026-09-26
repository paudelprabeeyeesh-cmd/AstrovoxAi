"""CQRS and event-sourced aggregates.

Provides:
- Command Bus with validation and middleware
- Query Bus with cache invalidation
- Event-sourced aggregates with versioning
- Aggregate roots with domain logic
- Read models from projections
"""

from __future__ import annotations

import copy
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CommandError(Exception):
    """Command validation or execution error."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        self.errors = errors or []
        super().__init__(message)


@dataclass
class Command:
    """Immutable command."""
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    issued_by: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Event:
    """Domain event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    aggregate_id: str = ""
    aggregate_type: str = ""
    version: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    caused_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Query:
    """Immutable query."""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    issued_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    """Query result."""
    query_id: str
    result: Any = None
    found: bool = False
    error: Optional[str] = None
    cache_hit: bool = False
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Middleware:
    """Command/Query middleware."""

    async def process_command(self, command: Command, next_handler: Callable[[Command], List[Event]]) -> List[Event]:
        return await next_handler(command)

    async def process_query(self, query: Query, next_handler: Callable[[Query], QueryResult]) -> QueryResult:
        return await next_handler(query)


class CommandBus:
    """Command bus with middleware and validation.

    Routes commands to handlers.
    """

    def __init__(self, middlewares: Optional[List[Middleware]] = None) -> None:
        self._handlers: Dict[str, Callable[[Command], List[Event]]] = {}
        self._validators: Dict[str, Callable[[Command], List[str]]] = {}
        self._middlewares = middlewares or []
        self._history: List[Command] = []
        self._lock = False

    def register(self, command_type: str, handler: Callable[[Command], List[Event]]) -> None:
        self._handlers[command_type] = handler

    def register_validator(self, command_type: str, validator: Callable[[Command], List[str]]) -> None:
        self._validators[command_type] = validator

    async def dispatch(self, command: Command) -> List[Event]:
        self._history.append(command)
        if len(self._history) > 10_000:
            self._history = self._history[-10_000:]

        if command.command_type not in self._handlers:
            raise CommandError(f"no handler for command: {command.command_type}")

        handler = self._handlers[command.command_type]

        if command.command_type in self._validators:
            errors = self._validators[command.command_type](command)
            if errors:
                raise CommandError(f"validation failed for {command.command_type}", errors=errors)

        async def execute(cmd: Command) -> List[Event]:
            return handler(cmd)

        for mw in reversed(self._middlewares):
            current = execute

            async def wrapped(cmd: Command, _mw=mw, _next=current) -> List[Event]:
                return await _mw.process_command(cmd, _next)

            execute = wrapped

        return await execute(command)

    def get_history(self, command_type: Optional[str] = None, limit: int = 100) -> List[Command]:
        commands = self._history
        if command_type:
            commands = [c for c in commands if c.command_type == command_type]
        return commands[-limit:]


class QueryBus:
    """Query bus with caching.

    Routes queries to handlers.
    """

    def __init__(self, cache_ttl_seconds: float = 60.0) -> None:
        self._handlers: Dict[str, Callable[[Query], QueryResult]] = {}
        self._cache: Dict[str, Tuple[QueryResult, float]] = {}
        self._cache_ttl = cache_ttl_seconds
        self._history: List[Query] = []
        self._lock = False

    def register(self, query_type: str, handler: Callable[[Query], QueryResult]) -> None:
        self._handlers[query_type] = handler

    async def execute(self, query: Query) -> QueryResult:
        self._history.append(query)
        if len(self._history) > 10_000:
            self._history = self._history[-10_000:]

        if query.query_type not in self._handlers:
            return QueryResult(query_id=query.query_id, error=f"no handler for query: {query.query_type}")

        handler = self._handlers[query.query_type]
        cache_key = f"{query.query_type}:{hash(frozenset(query.parameters.items()))}"

        if cache_key in self._cache:
            result, cached_at = self._cache[cache_key]
            if (time.time() - cached_at) < self._cache_ttl:
                result.cache_hit = True
                return result

        result = handler(query)
        self._cache[cache_key] = (result, time.time())
        return result

    def invalidate_cache(self, query_type: Optional[str] = None) -> None:
        if query_type is None:
            self._cache.clear()
        else:
            self._cache = {k: v for k, v in self._cache.items() if not k.startswith(query_type)}

    def get_history(self, query_type: Optional[str] = None, limit: int = 100) -> List[Query]:
        queries = self._history
        if query_type:
            queries = [q for q in queries if q.query_type == query_type]
        return queries[-limit:]


class EventSourcedAggregate:
    """Event-sourced aggregate with snapshot support.

    Provides:
    - Command handling with validation
    - Event application
    - Snapshot creation
    - Aggregate reconstruction from events
    """

    def __init__(
        self,
        aggregate_id: str,
        aggregate_type: str,
        event_store: Any,
        snapshot_engine: Optional[Any] = None,
        max_version: int = 0,
    ) -> None:
        self.aggregate_id = aggregate_id
        self.aggregate_type = aggregate_type
        self.event_store = event_store
        self.snapshot_engine = snapshot_engine
        self.version = max_version
        self._changes: List[Event] = []
        self._state: Dict[str, Any] = {}
        self._lock = False

    def apply(self, event: Event) -> None:
        self._changes.append(event)
        self.version = event.version
        self._apply(event)

    def _apply(self, event: Event) -> None:
        pass

    def _emit(self, event_type: str, payload: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Event:
        event = Event(
            event_type=event_type,
            aggregate_id=self.aggregate_id,
            aggregate_type=self.aggregate_type,
            version=self.version + 1,
            payload=payload,
            metadata=metadata or {},
        )
        self.apply(event)
        return event

    def get_uncommitted_events(self) -> List[Event]:
        return list(self._changes)

    def mark_committed(self) -> None:
        self._changes = []

    def get_state(self) -> Dict[str, Any]:
        return copy.deepcopy(self._state)

    def set_state(self, state: Dict[str, Any]) -> None:
        self._state = copy.deepcopy(state)

    def snapshot(self, metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        if self.snapshot_engine is None:
            return None
        return self.snapshot_engine.create_snapshot(
            aggregate_id=self.aggregate_id,
            aggregate_type=self.aggregate_type,
            version=self.version,
            state=self._state,
            event_position=self.version,
            metadata=metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "version": self.version,
            "state": self.get_state(),
            "uncommitted_events": len(self._changes),
        }


class CQRS:
    """CQRS engine.

    Provides:
    - Command validation and dispatch
    - Query execution with caching
    - Read model maintenance
    """

    def __init__(
        self,
        command_bus: Optional[CommandBus] = None,
        query_bus: Optional[QueryBus] = None,
    ) -> None:
        self.command_bus = command_bus or CommandBus()
        self.query_bus = query_bus or QueryBus()
        self._aggregates: Dict[str, EventSourcedAggregate] = {}
        self._read_models: Dict[str, Dict[str, Any]] = {}
        self._lock = False

    def register_aggregate(self, aggregate: EventSourcedAggregate) -> None:
        self._aggregates[aggregate.aggregate_id] = aggregate

    def get_aggregate(self, aggregate_id: str) -> Optional[EventSourcedAggregate]:
        return self._aggregates.get(aggregate_id)

    def set_read_model(self, model_name: str, data: Dict[str, Any]) -> None:
        self._read_models[model_name] = data

    def get_read_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        return self._read_models.get(model_name)

    def invalidate_read_model(self, model_name: str) -> None:
        if model_name in self._read_models:
            del self._read_models[model_name]

    async def execute(self, command: Command) -> List[Event]:
        return await self.command_bus.dispatch(command)

    async def query(self, query: Query) -> QueryResult:
        return await self.query_bus.execute(query)

    def rebuild_projections(self) -> int:
        count = 0
        for model_name, data in self._read_models.items():
            self._read_models[model_name] = {}
            count += 1
        return count

    def get_stats(self) -> Dict[str, Any]:
        return {
            "aggregates": len(self._aggregates),
            "read_models": len(self._read_models),
            "command_history": len(self.command_bus.get_history()),
            "query_history": len(self.query_bus.get_history()),
        }
