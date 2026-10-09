"""
CQRS pattern: command and query separation.

Provides separate write and read models, command handlers, and query handlers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar

T = TypeVar("T")


class CommandStatus(Enum):
    PENDING = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()


class QueryStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    READY = auto()
    ERROR = auto()


@dataclass
class CommandResult:
    command_id: str
    status: CommandStatus
    value: Any = None
    error: Optional[str] = None
    timestamp: str = ""
    duration_ms: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime_iso()


@dataclass
class QueryResult(Generic[T]):
    query_id: str
    status: QueryStatus
    value: Optional[T] = None
    error: Optional[str] = None
    timestamp: str = ""
    duration_ms: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime_iso()


def datetime_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Command:
    name: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Query(Generic[T]):
    name: str
    params: Dict[str, Any]
    result_type: Optional[type] = None


CommandHandler = Callable[[Command], CommandResult]
QueryHandler = Callable[[Query[T]], QueryResult[T]]


class CommandBus:
    def __init__(self) -> None:
        self._handlers: Dict[str, CommandHandler] = {}
        self._history: List[CommandResult] = []

    def register(self, name: str, handler: CommandHandler) -> None:
        self._handlers[name] = handler

    def dispatch(self, command: Command) -> CommandResult:
        handler = self._handlers.get(command.name)
        if handler is None:
            result = CommandResult(
                command_id=command.payload.get("command_id", ""),
                status=CommandStatus.FAILED,
                error="handler not found",
            )
            self._history.append(result)
            return result
        start = time.time()
        value = handler(command)
        duration = (time.time() - start) * 1000
        status = CommandStatus.COMPLETED if value is None or value.get("status") != CommandStatus.FAILED else CommandStatus.FAILED
        result = CommandResult(
            command_id=command.payload.get("command_id", ""),
            status=status,
            value=value,
            duration_ms=duration,
        )
        self._history.append(result)
        return result

    def history(self) -> List[CommandResult]:
        return list(self._history)


class QueryBus:
    def __init__(self) -> None:
        self._handlers: Dict[str, QueryHandler] = {}
        self._history: List[QueryResult] = []
        self._cache: Dict[str, Tuple[QueryResult, float]] = {}
        self._cache_ttl: float = 30.0

    def register(self, name: str, handler: QueryHandler) -> None:
        self._handlers[name] = handler

    def ask(self, query: Query[T], use_cache: bool = True) -> QueryResult[T]:
        key = f"{query.name}:{json.dumps(query.params, sort_keys=True)}"
        if use_cache and key in self._cache:
            cached, ts = self._cache[key]
            if time.time() - ts <= self._cache_ttl:
                return cached
        handler = self._handlers.get(query.name)
        if handler is None:
            result = QueryResult[T](
                query_id=query.params.get("query_id", ""),
                status=QueryStatus.ERROR,
                error="handler not found",
            )
            self._history.append(result)
            return result
        start = time.time()
        value = handler(query)
        duration = (time.time() - start) * 1000
        result = QueryResult[T](
            query_id=query.params.get("query_id", ""),
            status=QueryStatus.READY,
            value=value,
            duration_ms=duration,
        )
        self._history.append(result)
        self._cache[key] = (result, time.time())
        return result

    def history(self) -> List[QueryResult]:
        return list(self._history)


import json


@dataclass
class ReadModel:
    name: str
    projection: Dict[str, Any] = field(default_factory=dict)
    version: int = 0

    def apply(self, event: Dict[str, Any]) -> None:
        key = event.get("key")
        if key is not None:
            self.projection[key] = event.get("value")
        self.version += 1


class EventualConsistencySync:
    def __init__(self, read_model: ReadModel) -> None:
        self.read_model = read_model
        self._pending: List[Dict[str, Any]] = []

    def enqueue(self, event: Dict[str, Any]) -> None:
        self._pending.append(event)

    def apply_pending(self) -> None:
        for event in self._pending:
            self.read_model.apply(event)
        self._pending.clear()
