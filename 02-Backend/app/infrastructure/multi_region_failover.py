"""Multi-region failover."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class RegionStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"


@dataclass
class Region:
    region_id: str
    name: str
    provider: str
    status: RegionStatus = RegionStatus.HEALTHY
    active: bool = True
    priority: int = 0
    endpoints: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FailoverManager:
    """Manage multi-region failover."""

    _regions: Dict[str, Region] = {}

    @classmethod
    def register_region(cls, region: Region) -> None:
        cls._regions[region.region_id] = region

    @classmethod
    def set_status(cls, region_id: str, status: RegionStatus) -> None:
        region = cls._regions.get(region_id)
        if region:
            region.status = status

    @classmethod
    def get_active_regions(cls) -> List[Region]:
        return [r for r in cls._regions.values() if r.active and r.status == RegionStatus.HEALTHY]

    @classmethod
    def get_failover_target(cls, source_region_id: str) -> Optional[Region]:
        active = cls.get_active_regions()
        source = cls._regions.get(source_region_id)
        if not source:
            return None
        candidates = [r for r in active if r.region_id != source_region_id and r.priority > source.priority]
        if not candidates:
            candidates = [r for r in active if r.region_id != source_region_id]
        if candidates:
            candidates.sort(key=lambda r: r.priority, reverse=True)
            return candidates[0]
        return None


_failover_manager: Optional[FailoverManager] = None


def get_failover_manager() -> FailoverManager:
    global _failover_manager
    if _failover_manager is None:
        _failover_manager = FailoverManager()
    return _failover_manager
