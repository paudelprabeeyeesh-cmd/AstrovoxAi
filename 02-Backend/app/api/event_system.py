"""Event bus and pub/sub system."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class Event:
    id: str
    type: str
    payload: dict
    source: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Subscription:
    id: str
    event_type: str
    handler: Callable
    active: bool = True


class EventBus:
    def __init__(self):
        self._subscriptions: Dict[str, list[Subscription]] = {}
        self._history: list[Event] = []

    def subscribe(self, event_type: str, handler: Callable) -> Subscription:
        sub_id = str(uuid.uuid4())
        subscription = Subscription(id=sub_id, event_type=event_type, handler=handler)
        self._subscriptions.setdefault(event_type, []).append(subscription)
        self._persist_subscription(subscription)
        return subscription

    def unsubscribe(self, subscription_id: str) -> bool:
        for event_type, subs in self._subscriptions.items():
            for sub in subs:
                if sub.id == subscription_id:
                    subs.remove(sub)
                    return True
        return False

    def publish(self, event_type: str, payload: dict, source: Optional[str] = None, metadata: Optional[dict] = None) -> list[Any]:
        event = Event(id=str(uuid.uuid4()), type=event_type, payload=payload, source=source, metadata=metadata or {})
        self._history.append(event)
        if len(self._history) > 10000:
            self._history = self._history[-10000:]
        results = []
        for sub in self._subscriptions.get(event_type, []):
            if not sub.active:
                continue
            try:
                if asyncio.iscoroutinefunction(sub.handler):
                    results.append(asyncio.run(sub.handler(event)))
                else:
                    results.append(sub.handler(event))
            except Exception as exc:
                logger.error("Event handler %s failed: %s", sub.id, exc)
        return results

    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> list[dict]:
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return [{"id": e.id, "type": e.type, "source": e.source, "timestamp": e.timestamp, "payload": e.payload} for e in events[-limit:]]

    def _persist_subscription(self, subscription: Subscription):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO event_subscriptions (id, event_type, handler_name, active) VALUES (?, ?, ?, ?)",
                (subscription.id, subscription.event_type, subscription.handler.__name__, 1 if subscription.active else 0),
            )
            conn.commit()


event_bus = EventBus()
