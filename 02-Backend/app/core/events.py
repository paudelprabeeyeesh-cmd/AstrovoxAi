"""Event bus for pub/sub messaging within the application."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


EventHandler = Callable[[Dict[str, Any]], Awaitable[None]]


class EventBus:
    """Async event bus for pub/sub messaging."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._middleware: List[Callable[[Dict[str, Any]], Dict[str, Any]]] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type."""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                pass

    def add_middleware(self, middleware: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Add middleware that processes events before they reach handlers."""
        self._middleware.append(middleware)

    async def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": payload.get("timestamp"),
        }
        for middleware in self._middleware:
            event = middleware(event)
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logger.debug(f"No handlers for event: {event_type}")
            return
        tasks = [handler(event["payload"]) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(f"Handler failed for event {event_type}: {result}")

    async def publish_async(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Alias for publish for consistency."""
        await self.publish(event_type, payload)


event_bus = EventBus()


def get_event_bus() -> EventBus:
    return event_bus
