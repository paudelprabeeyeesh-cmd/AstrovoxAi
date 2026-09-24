"""
Event sourcing with event store.

Records events, supports event replay, and materializes read projections.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass
class Event:
    aggregate_id: str
    event_type: str
    payload: Dict[str, Any]
    version: int = 1
    stream: str = "default"
    timestamp: str = ""
    event_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.event_id:
            self.event_id = hashlib.sha256(
                f"{self.aggregate_id}:{self.event_type}:{self.timestamp}:{self.version}".encode()
            ).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "aggregate_id": self.aggregate_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "version": self.version,
            "stream": self.stream,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class EventStore:
    def __init__(self) -> None:
        self._streams: Dict[str, List[Event]] = {}
        self._subscribers: List[Callable[[Event], None]] = []
        self._checkpoints: Dict[str, int] = {}

    def append(self, event: Event) -> None:
        stream = event.stream
        self._streams.setdefault(stream, []).append(event)
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception:
                continue

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        self._subscribers.append(handler)

    def read_stream(self, stream: str, from_version: int = 0, limit: int = 1000) -> List[Event]:
        events = self._streams.get(stream, [])
        return [e for e in events if e.version >= from_version][:limit]

    def read_aggregate(self, aggregate_id: str) -> List[Event]:
        result: List[Event] = []
        for events in self._streams.values():
            for e in events:
                if e.aggregate_id == aggregate_id:
                    result.append(e)
        return sorted(result, key=lambda e: e.version)

    def project(self, stream: str, builder: Callable[[List[Event]], Any]) -> Any:
        events = self.read_stream(stream)
        return builder(events)

    def checkpoint(self, stream: str, version: int) -> None:
        self._checkpoints[stream] = version

    def replay(self, stream: str, applier: Callable[[Event], None]) -> None:
        for event in self.read_stream(stream):
            applier(event)


class EventProjection:
    def __init__(self, event_store: EventStore) -> None:
        self.event_store = event_store
        self._projection: Dict[str, Any] = {}

    def build(self, stream: str, initial: Any = None) -> Any:
        def builder(events: List[Event]) -> Any:
            state = initial if initial is not None else {}
            for event in events:
                state = self._apply(state, event)
            return state

        self._projection[stream] = self.event_store.project(stream, builder)
        return self._projection[stream]

    def _apply(self, state: Any, event: Event) -> Any:
        if isinstance(state, dict):
            if "append" in event.payload:
                key = event.payload["key"]
                state[key] = event.payload["value"]
            elif "key" in event.payload and "value" in event.payload:
                state[event.payload["key"]] = event.payload["value"]
        elif isinstance(state, list):
            state.append(event.payload)
        return state
