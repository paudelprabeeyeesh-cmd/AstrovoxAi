"""Event-driven automation engine."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EventHandler:
    handler_id: str
    event_type: str
    func: Callable[[Dict[str, Any]], Any]
    filters: Dict[str, Any] = field(default_factory=dict)


class EventDrivenEngine:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}

    def register(self, handler: EventHandler) -> None:
        self._handlers.setdefault(handler.event_type, []).append(handler)

    async def emit(self, event_type: str, event: Dict[str, Any]) -> None:
        for handler in self._handlers.get(event_type, []):
            if self._matches(handler.filters, event):
                try:
                    result = handler.func(event)
                    if result is not None and hasattr(result, '__await__'):
                        await result
                except Exception:
                    logger.exception("event handler %s failed", handler.handler_id)

    def _matches(self, filters: Dict[str, Any], event: Dict[str, Any]) -> bool:
        return all(event.get(k) == v for k, v in filters.items())


event_driven_engine = EventDrivenEngine()
