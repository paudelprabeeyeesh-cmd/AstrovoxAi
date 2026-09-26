"""Multi-region replication and conflict resolution."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RegionRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DR = "disaster_recovery"


@dataclass
class RegionConfig:
    region_id: str
    endpoint: str
    role: RegionRole
    priority: int = 0
    lag: float = 0.0


@dataclass
class ReplicationEvent:
    region_id: str
    operation: str
    key: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    version: int = 1


class ConflictResolutionStrategy(str, Enum):
    LAST_WRITE_WINS = "last_write_wins"
    PRIMARY_WINS = "primary_wins"
    CUSTOM_MERGE = "custom_merge"


class ReplicationManager:
    def __init__(
        self,
        regions: List[RegionConfig],
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS,
    ):
        self._regions = {r.region_id: r for r in regions}
        self._primary = next((r for r in regions if r.role == RegionRole.PRIMARY), None)
        self._secondaries = [r for r in regions if r.role == RegionRole.SECONDARY]
        self._dr = [r for r in regions if r.role == RegionRole.DR]
        self._event_log: List[ReplicationEvent] = []
        self._conflict_strategy = conflict_strategy

    def primary(self) -> Optional[RegionConfig]:
        return self._primary

    def secondaries(self) -> List[RegionConfig]:
        return list(self._secondaries)

    def append_event(self, event: ReplicationEvent) -> None:
        self._event_log.append(event)
        self._propagate(event)

    def _propagate(self, event: ReplicationEvent) -> None:
        for region in self._secondaries + self._dr:
            lag = time.time() - event.timestamp
            region.lag = lag
            logger.debug("Replicated %s to %s (lag=%.3fs)", event.operation, region.region_id, lag)

    def resolve_conflict(self, local: ReplicationEvent, remote: ReplicationEvent) -> ReplicationEvent:
        if self._conflict_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            return local if local.timestamp >= remote.timestamp else remote
        if self._conflict_strategy == ConflictResolutionStrategy.PRIMARY_WINS:
            return local if self._primary and local.region_id == self._primary.region_id else remote
        merged = ReplicationEvent(
            region_id=f"{local.region_id}+{remote.region_id}",
            operation=local.operation,
            key=local.key,
            payload={**local.payload, **remote.payload},
            timestamp=max(local.timestamp, remote.timestamp),
            version=max(local.version, remote.version) + 1,
        )
        return merged

    def get_replication_lag(self, region_id: str) -> float:
        region = self._regions.get(region_id)
        return region.lag if region else -1.0

    def status(self) -> Dict[str, Any]:
        return {
            "primary": self._primary.region_id if self._primary else None,
            "secondaries": [r.region_id for r in self._secondaries],
            "dr": [r.region_id for r in self._dr],
            "event_log_size": len(self._event_log),
            "conflict_strategy": self._conflict_strategy.value,
        }
