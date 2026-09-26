"""Edge synchronization for distributed edge nodes."""
from __future__ import annotations

import logging
import queue
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncQueue:
    node_id: str
    pending: List[Dict[str, Any]] = field(default_factory=list)
    synced_at: Optional[datetime] = None


class EdgeSync:
    def __init__(self) -> None:
        self._queues: Dict[str, SyncQueue] = {}

    def enqueue(self, node_id: str, payload: Dict[str, Any]) -> None:
        queue_ = self._queues.setdefault(node_id, SyncQueue(node_id=node_id))
        queue_.pending.append(payload)

    async def sync(self, node_id: str) -> Optional[SyncQueue]:
        queue_ = self._queues.get(node_id)
        if queue_ and queue_.pending:
            queue_.synced_at = datetime.now(timezone.utc)
            queue_.pending = []
            return queue_
        return None


edge_sync = EdgeSync()
