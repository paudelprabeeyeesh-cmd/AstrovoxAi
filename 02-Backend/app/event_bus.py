<<<<<<< HEAD
"""Event bus for pub/sub messaging."""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio


class EventType(Enum):
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    CHAT_MESSAGE = "chat.message"
    MEMORY_STORED = "memory.stored"
    BILLING_INVOICE = "billing.invoice"
    NOTIFICATION_SENT = "notification.sent"
    AGENT_COMPLETED = "agent.completed"
    SYSTEM_ALERT = "system.alert"
=======
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
>>>>>>> 10617909505295e4a37b817bb54db2364934b978


@dataclass
class Event:
<<<<<<< HEAD
    event_id: str
    event_type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventBus:
    _subscribers: Dict[EventType, List[Callable]] = {}
    _history: List[Event] = []
    _max_history = 10000

    @classmethod
    def subscribe(cls, event_type: EventType, callback: Callable) -> None:
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(callback)

    @classmethod
    def unsubscribe(cls, event_type: EventType, callback: Callable) -> None:
        if event_type in cls._subscribers:
            cls._subscribers[event_type] = [c for c in cls._subscribers[event_type] if c != callback]

    @classmethod
    async def publish(cls, event: Event) -> None:
        cls._history.append(event)
        if len(cls._history) > cls._max_history:
            cls._history = cls._history[-cls._max_history:]
        callbacks = cls._subscribers.get(event.event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception:
                pass

    @classmethod
    def publish_sync(cls, event: Event) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(cls.publish(event))
        except RuntimeError:
            asyncio.run(cls.publish(event))

    @classmethod
    def get_history(cls, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        events = cls._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]
=======
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
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
