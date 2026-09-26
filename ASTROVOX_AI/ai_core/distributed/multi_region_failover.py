"""Multi-region failover for high availability."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RegionStatus(Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class RegionConfig:
    region_id: str
    region_name: str
    priority: int = 0
    endpoint: str = ""
    health_check_url: str = "/health"
    failover_timeout: float = 30.0
    health_check_interval: float = 10.0


class MultiRegionFailover:
    def __init__(self, regions: List[RegionConfig], health_check_fn: Optional[Callable[[str], bool]] = None):
        self.regions = {r.region_id: r for r in regions}
        self.health_check_fn = health_check_fn
        self._region_status: Dict[str, RegionStatus] = {r.region_id: RegionStatus.ACTIVE if r.priority == max(r.priority for r in regions) else RegionStatus.STANDBY for r in regions}
        self._active_region: Optional[str] = None
        self._failover_history: List[Dict[str, Any]] = []
        for rid, status in self._region_status.items():
            if status == RegionStatus.ACTIVE:
                self._active_region = rid
                break

    def get_active_region(self) -> Optional[str]:
        return self._active_region

    def check_region_health(self, region_id: str) -> RegionStatus:
        if self.health_check_fn:
            try:
                healthy = self.health_check_fn(region_id)
                return RegionStatus.ACTIVE if healthy else RegionStatus.FAILED
            except Exception:
                return RegionStatus.FAILED
        return RegionStatus.ACTIVE

    def run_health_checks(self) -> Dict[str, RegionStatus]:
        results = {}
        for region_id in self.regions:
            status = self.check_region_health(region_id)
            self._region_status[region_id] = status
            results[region_id] = status
            if status == RegionStatus.FAILED and self._active_region == region_id:
                self._initiate_failover(region_id)
        return results

    def _initiate_failover(self, failed_region: str) -> None:
        logger.warning("Initiating failover from region %s", failed_region)
        candidates = sorted(
            [(rid, self.regions[rid]) for rid, status in self._region_status.items() if status == RegionStatus.ACTIVE and rid != failed_region],
            key=lambda x: x[1].priority,
            reverse=True,
        )
        if candidates:
            new_active = candidates[0][0]
            self._active_region = new_active
            self._region_status[failed_region] = RegionStatus.FAILED
            self._failover_history.append({
                "from_region": failed_region,
                "to_region": new_active,
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.info("Failover complete: %s -> %s", failed_region, new_active)

    def get_region_status(self) -> Dict[str, Any]:
        return {
            "active_region": self._active_region,
            "regions": {rid: {"status": status.value, "priority": self.regions[rid].priority, "endpoint": self.regions[rid].endpoint} for rid, status in self._region_status.items()},
            "failover_count": len(self._failover_history),
        }

    def get_failover_history(self) -> List[Dict[str, Any]]:
        return self._failover_history.copy()
