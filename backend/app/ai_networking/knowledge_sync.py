"""Knowledge synchronization across distributed nodes."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncEvent:
    event_id: str
    node_id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeSync:
    def __init__(self) -> None:
        self._events: List[SyncEvent] = []
        self._subscribers: List[Any] = []

    def publish(self, node_id: str, event_type: str, payload: Dict[str, Any]) -> SyncEvent:
        event = SyncEvent(event_id=uuid.uuid4().hex, node_id=node_id, event_type=event_type, payload=payload)
        self._events.append(event)
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception:
                logger.exception("subscriber failed on sync event")
        return event

    def subscribe(self, handler: Any) -> None:
        self._subscribers.append(handler)

    def get_events(self, node_id: Optional[str] = None, event_type: Optional[str] = None) -> List[SyncEvent]:
        events = self._events
        if node_id:
            events = [e for e in events if e.node_id == node_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events


knowledge_sync = KnowledgeSync()
