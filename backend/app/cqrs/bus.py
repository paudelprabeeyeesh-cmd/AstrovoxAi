"""CQRS pattern implementation for read/write separation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Command:
    command_id: str
    command_type: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Query:
    query_id: str
    query_type: str
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 100
    offset: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    query_id: str
    items: List[Dict[str, Any]]
    total: int
    took_ms: float
    cached: bool = False


class CQRSBus:
    def __init__(self) -> None:
        self._command_handlers: Dict[str, Callable[..., Any]] = {}
        self._query_handlers: Dict[str, Callable[..., Any]] = {}
        self._read_model: Dict[str, List[Dict[str, Any]]] = {}
        self._event_log: List[Dict[str, Any]] = []

    def register_command_handler(self, command_type: str, handler: Callable[..., Any]) -> None:
        self._command_handlers[command_type] = handler

    def register_query_handler(self, query_type: str, handler: Callable[..., Any]) -> None:
        self._query_handlers[query_type] = handler

    async def execute_command(self, command: Command) -> Any:
        handler = self._command_handlers.get(command.command_type)
        if not handler:
            raise ValueError(f"No handler for command: {command.command_type}")
        result = await self._call(handler, command.payload)
        self._event_log.append({
            "type": "command",
            "command_id": command.command_id,
            "command_type": command.command_type,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        return result

    async def execute_query(self, query: Query) -> QueryResult:
        handler = self._query_handlers.get(query.query_type)
        if not handler:
            raise ValueError(f"No handler for query: {query.query_type}")
        start = datetime.now(timezone.utc)
        items = await self._call(handler, query)
        took = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        total = len(items) if hasattr(items, "__len__") else 0
        return QueryResult(query_id=query.query_id, items=items[query.offset:query.offset + query.limit], total=total, took_ms=took)

    def update_read_model(self, entity_type: str, item: Dict[str, Any]) -> None:
        self._read_model.setdefault(entity_type, []).append(item)

    def query_read_model(self, entity_type: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = self._read_model.get(entity_type, [])
        for key, value in filters.items():
            items = [item for item in items if item.get(key) == value]
        return items

    @staticmethod
    async def _call(func: Callable[..., Any], payload: Any) -> Any:
        import inspect
        sig = inspect.signature(func)
        if asyncio.iscoroutinefunction(func):
            if "payload" in sig.parameters:
                return await func(payload)
            return await func()
        else:
            if "payload" in sig.parameters:
                return func(payload)
            return func()


import asyncio

cqrs_bus = CQRSBus()
