"""Event bus for internal pub/sub."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Event:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    retries: int = 0
    max_retries: int = 3


EventListener = Callable[[Event], Awaitable[None]]


class EventBus:
    """Async event bus with topics and retry."""

    def __init__(self):
        self._subscribers: Dict[str, List[EventListener]] = {}
        self._middleware: List[Callable[[Event], Event]] = []

    def subscribe(self, event_type: str, listener: EventListener) -> None:
        self._subscribers.setdefault(event_type, []).append(listener)
        logger.debug("Subscribed to %s", event_type)

    def unsubscribe(self, event_type: str, listener: EventListener) -> None:
        listeners = self._subscribers.get(event_type, [])
        if listener in listeners:
            listeners.remove(listener)

    def add_middleware(self, middleware: Callable[[Event], Event]) -> None:
        self._middleware.append(middleware)

    async def publish(self, event: Event) -> None:
        for middleware in self._middleware:
            event = middleware(event)
        listeners = self._subscribers.get(event.event_type, [])
        if not listeners:
            logger.debug("No listeners for %s", event.event_type)
            return
        tasks = []
        for listener in listeners:
            tasks.append(self._safe_invoke(listener, event))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_invoke(self, listener: EventListener, event: Event) -> None:
        try:
            await listener(event)
        except Exception as exc:  # noqa: BLE001
            logger.error("Event listener failed for %s: %s", event.event_type, exc)
            if event.retries < event.max_retries:
                event.retries += 1
                await asyncio.sleep(0.5 * (2 ** event.retries))
                await self._safe_invoke(listener, event)


event_bus = EventBus()
