"""Snapshot engine for state persistence and point-in-time queries.

Provides:
- Snapshot creation and storage
- State point extraction
- Snapshot compaction and retention
- State hydration from snapshots
"""

from __future__ import annotations

import copy
import gzip
import logging
import pickle
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SnapshotStrategy(Enum):
    """When to create snapshots."""

    EVERY_N_EVENTS = "every_n_events"
    TIME_INTERVAL = "time_interval"
    SIZE_THRESHOLD = "size_threshold"
    HYBRID = "hybrid"


@dataclass
class Snapshot:
    """Immutable snapshot of aggregate state."""

    snapshot_id: str
    aggregate_id: str
    aggregate_type: str
    version: int
    state: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    size_bytes: int = 0
    compressed: bool = False

    def to_bytes(self) -> bytes:
        """Serialize snapshot to bytes."""
        data = pickle.dumps(self)
        if self.compressed:
            return gzip.compress(data)
        return data

    @classmethod
    def from_bytes(cls, data: bytes, compressed: bool = True) -> "Snapshot":
        """Deserialize snapshot from bytes."""
        if compressed:
            data = gzip.decompress(data)
        return pickle.loads(data)


@dataclass
class StatePoint:
    """Point in time for state queries."""

    timestamp: datetime
    version: int
    snapshot_id: str
    aggregate_id: str
    event_position: int
    state: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "snapshot_id": self.snapshot_id,
            "aggregate_id": self.aggregate_id,
            "event_position": self.event_position,
            "state": self.state,
        }


class SnapshotEngine:
    """Snapshot creation, storage, and retrieval.

    Supports:
    - Multiple snapshot strategies
    - Compaction and retention
    - State point extraction
    - Snapshot indexing
    """

    def __init__(
        self,
        strategy: SnapshotStrategy = SnapshotStrategy.HYBRID,
        every_n_events: int = 100,
        time_interval_seconds: float = 3600.0,
        size_threshold_bytes: int = 10_000_000,
        retention_policy: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._strategy = strategy
        self._every_n_events = every_n_events
        self._time_interval = time_interval_seconds
        self._size_threshold = size_threshold_bytes
        self._retention_policy = retention_policy or {"max_snapshots": 100, "ttl_days": 30}
        self._snapshots: Dict[str, List[Snapshot]] = {}  # aggregate_id -> snapshots
        self._state_points: Dict[str, List[StatePoint]] = {}  # aggregate_id -> state points
        self._event_counts: Dict[str, int] = {}
        self._last_snapshot_time: Dict[str, float] = {}
        self._size_tracker: Dict[str, int] = {}
        self._lock = False

    def should_create_snapshot(self, aggregate_id: str, event_count: int) -> bool:
        """Determine if snapshot should be created."""
        if self._strategy == SnapshotStrategy.EVERY_N_EVENTS:
            return self._event_counts.get(aggregate_id, 0) >= self._every_n_events

        if self._strategy == SnapshotStrategy.TIME_INTERVAL:
            last = self._last_snapshot_time.get(aggregate_id, 0)
            return (time.time() - last) >= self._time_interval

        if self._strategy == SnapshotStrategy.SIZE_THRESHOLD:
            return self._size_tracker.get(aggregate_id, 0) >= self._size_threshold

        if self._strategy == SnapshotStrategy.HYBRID:
            n_events = self._event_counts.get(aggregate_id, 0) >= self._every_n_events
            time_ok = (time.time() - self._last_snapshot_time.get(aggregate_id, 0)) >= self._time_interval
            size_ok = self._size_tracker.get(aggregate_id, 0) >= self._size_threshold
            return n_events or time_ok or size_ok

        return False

    def create_snapshot(
        self,
        aggregate_id: str,
        aggregate_type: str,
        version: int,
        state: Dict[str, Any],
        event_position: int,
        metadata: Optional[Dict[str, Any]] = None,
        compressed: bool = True,
    ) -> Snapshot:
        """Create snapshot of aggregate state."""
        import uuid

        snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            version=version,
            state=copy.deepcopy(state),
            metadata=metadata or {},
            compressed=compressed,
            size_bytes=len(pickle.dumps(state)),
        )

        if aggregate_id not in self._snapshots:
            self._snapshots[aggregate_id] = []

        self._snapshots[aggregate_id].append(snapshot)

        state_point = StatePoint(
            timestamp=snapshot.created_at,
            version=version,
            snapshot_id=snapshot.snapshot_id,
            aggregate_id=aggregate_id,
            event_position=event_position,
            state=copy.deepcopy(state),
        )

        if aggregate_id not in self._state_points:
            self._state_points[aggregate_id] = []

        self._state_points[aggregate_id].append(state_point)

        self._event_counts[aggregate_id] = 0
        self._last_snapshot_time[aggregate_id] = time.time()
        self._size_tracker[aggregate_id] = 0

        logger.info(
            "created snapshot %s for aggregate %s v%d",
            snapshot.snapshot_id,
            aggregate_id,
            version,
        )
        return snapshot

    def record_event(self, aggregate_id: str, event_size_bytes: int = 0) -> None:
        """Record event for snapshot decision making."""
        self._event_counts[aggregate_id] = self._event_counts.get(aggregate_id, 0) + 1
        self._size_tracker[aggregate_id] = self._size_tracker.get(aggregate_id, 0) + event_size_bytes

    def get_snapshot(self, aggregate_id: str, snapshot_id: str) -> Optional[Snapshot]:
        """Get specific snapshot by ID."""
        for snapshot in self._snapshots.get(aggregate_id, []):
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        return None

    def get_latest_snapshot(self, aggregate_id: str) -> Optional[Snapshot]:
        """Get latest snapshot for aggregate."""
        snapshots = self._snapshots.get(aggregate_id, [])
        if not snapshots:
            return None
        return snapshots[-1]

    def get_snapshot_at(self, aggregate_id: str, version: int) -> Optional[Snapshot]:
        """Get snapshot closest to version."""
        snapshots = self._snapshots.get(aggregate_id, [])
        if not snapshots:
            return None
        return max(snapshots, key=lambda s: s.version <= version)

    def get_state_at_version(self, aggregate_id: str, version: int) -> Optional[StatePoint]:
        """Get state point closest to version."""
        state_points = self._state_points.get(aggregate_id, [])
        if not state_points:
            return None
        return max((sp for sp in state_points if sp.version <= version), key=lambda sp: sp.version, default=None)

    def get_state_at_timestamp(self, aggregate_id: str, timestamp: datetime) -> Optional[StatePoint]:
        """Get state point closest to timestamp."""
        state_points = self._state_points.get(aggregate_id, [])
        if not state_points:
            return None
        return max(
            (sp for sp in state_points if sp.timestamp <= timestamp),
            key=lambda sp: sp.timestamp,
            default=None,
        )

    def get_state_at_event_position(self, aggregate_id: str, event_position: int) -> Optional[StatePoint]:
        """Get state point closest to event position."""
        state_points = self._state_points.get(aggregate_id, [])
        if not state_points:
            return None
        return max(
            (sp for sp in state_points if sp.event_position <= event_position),
            key=lambda sp: sp.event_position,
            default=None,
        )

    def get_snapshots(self, aggregate_id: str) -> List[Snapshot]:
        """Get all snapshots for aggregate."""
        return list(self._snapshots.get(aggregate_id, []))

    def get_state_points(self, aggregate_id: str) -> List[StatePoint]:
        """Get all state points for aggregate."""
        return list(self._state_points.get(aggregate_id, []))

    def compact(self, aggregate_id: str, keep_n: int = 10) -> int:
        """Compact snapshots, keeping only N most recent."""
        if aggregate_id not in self._snapshots:
            return 0
        before = len(self._snapshots[aggregate_id])
        self._snapshots[aggregate_id] = self._snapshots[aggregate_id][-keep_n:]
        after = len(self._snapshots[aggregate_id])
        logger.info("compacted %d -> %d snapshots for %s", before, after, aggregate_id)
        return before - after

    def apply_retention(self) -> Dict[str, int]:
        """Apply retention policy to all aggregates."""
        removed = {}
        max_snapshots = self._retention_policy.get("max_snapshots", 100)
        ttl_days = self._retention_policy.get("ttl_days", 30)
        ttl_seconds = ttl_days * 86400
        now = time.time()

        for aggregate_id, snapshots in self._snapshots.items():
            original_count = len(snapshots)
            cutoff = now - ttl_seconds

            snapshots = [
                s for s in snapshots
                if (now - s.created_at.timestamp()) <= ttl_seconds
            ]
            snapshots = snapshots[-max_snapshots:]
            self._snapshots[aggregate_id] = snapshots

            removed_count = original_count - len(snapshots)
            if removed_count > 0:
                removed[aggregate_id] = removed_count

        return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get snapshot statistics."""
        total_snapshots = sum(len(v) for v in self._snapshots.values())
        total_state_points = sum(len(v) for v in self._state_points.values())
        total_state_bytes = sum(s.size_bytes for s in self._snapshots)
        return {
            "aggregates": len(self._snapshots),
            "total_snapshots": total_snapshots,
            "total_state_points": total_state_points,
            "total_state_bytes": total_state_bytes,
            "strategy": self._strategy.value,
        }
