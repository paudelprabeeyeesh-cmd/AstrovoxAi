"""Event bus for pub/sub messaging."""

from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import uuid


class EventType(Enum):
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    CHAT_MESSAGE = "chat.message"
    MEMORY_STORED = "memory.stored"
    BILLING_INVOICE = "billing.invoice"
    NOTIFICATION_SENT = "notification.sent"
    AGENT_COMPLETED = "agent.completed"
    SYSTEM_ALERT = "system.alert"


@dataclass
class Event:
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
