"""Realtime sync engine for distributed state."""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncEvent:
    event_id: str
    entity_type: str
    entity_id: str
    operation: str
    data: Dict[str, Any]
    checksum: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = hashlib.sha256(str(self.data).encode()).hexdigest()


@dataclass
class SyncNode:
    node_id: str
    last_sync: Optional[datetime] = None
    version: int = 0


class RealtimeSync:
    def __init__(self) -> None:
        self._nodes: Dict[str, SyncNode] = {}
        self._events: List[SyncEvent] = []
        self._state: Dict[str, Dict[str, Any]] = {}

    def register_node(self, node_id: str) -> None:
        self._nodes[node_id] = SyncNode(node_id=node_id)

    def push_event(self, event: SyncEvent) -> None:
        self._events.append(event)
        self._apply(event)

    def pull_changes(self, node_id: str, since_version: int = 0) -> List[SyncEvent]:
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [e for e in self._events if e.timestamp > (node.last_sync or datetime.min.replace(tzinfo=timezone.utc))]

    def apply_remote(self, node_id: str, event: SyncEvent) -> None:
        current = self._state.get(event.entity_type, {}).get(event.entity_id)
        if current and current.get("checksum") == event.checksum:
            return
        self._state.setdefault(event.entity_type, {})[event.entity_id] = {"data": event.data, "checksum": event.checksum}
        node = self._nodes.get(node_id)
        if node:
            node.last_sync = datetime.now(timezone.utc)
            node.version += 1

    def get_state(self, entity_type: str, entity_id: str) -> Optional[Dict[str, Any]]:
        return self._state.get(entity_type, {}).get(entity_id)

    def _apply(self, event: SyncEvent) -> None:
        self._state.setdefault(event.entity_type, {})[event.entity_id] = {"data": event.data, "checksum": event.checksum}


realtime_sync = RealtimeSync()
