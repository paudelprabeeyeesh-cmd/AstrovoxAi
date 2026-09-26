"""Event sourcing for audit trail and state reconstruction."""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Event:
    event_id: str
    aggregate_id: str
    event_type: str
    data: Dict[str, Any]
    version: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventStore:
    def __init__(self) -> None:
        self._events: List[Event] = []
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._subscribers: Dict[str, List[Callable[..., Any]]] = {}

    def append(self, event: Event) -> None:
        event.version = len([e for e in self._events if e.aggregate_id == event.aggregate_id]) + 1
        self._events.append(event)
        self._notify(event)

    def get_events(self, aggregate_id: str, since_version: int = 0) -> List[Event]:
        return [e for e in self._events if e.aggregate_id == aggregate_id and e.version > since_version]

    def save_snapshot(self, aggregate_id: str, state: Dict[str, Any], version: int) -> None:
        self._snapshots[aggregate_id] = {"state": copy.deepcopy(state), "version": version}

    def load_snapshot(self, aggregate_id: str) -> Optional[Dict[str, Any]]:
        snapshot = self._snapshots.get(aggregate_id)
        return snapshot["state"] if snapshot else None

    def subscribe(self, event_type: str, handler: Callable[..., Any]) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def _notify(self, event: Event) -> None:
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Event handler failed for %s", event.event_type)

    def rebuild_state(self, aggregate_id: str) -> Dict[str, Any]:
        state = self.load_snapshot(aggregate_id) or {}
        events = self.get_events(aggregate_id)
        for event in events:
            state = self._apply(state, event)
        return state

    @staticmethod
    def _apply(state: Dict[str, Any], event: Event) -> Dict[str, Any]:
        handler_name = f"apply_{event.event_type}"
        handler = getattr(EventSourcedAggregate, handler_name, None)
        if handler:
            return handler(state, event.data)
        return {**state, **event.data}


class EventSourcedAggregate:
    @staticmethod
    def apply_created(state: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        return {**state, **data}

    @staticmethod
    def apply_updated(state: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        return {**state, **data}

    @staticmethod
    def apply_deleted(state: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        return {**state, "deleted": True}


event_store = EventStore()
