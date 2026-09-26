"""Multi-region failover and disaster recovery for distributed inference."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RegionStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    FAILING_OVER = "failing_over"


@dataclass
class Region:
    region_id: str
    endpoint: str
    priority: int = 0
    status: RegionStatus = RegionStatus.HEALTHY
    health_check_interval: float = 10.0
    last_health_check: datetime = field(default_factory=datetime.utcnow)
    active_connections: int = 0
    failed_requests: int = 0


class MultiRegionFailover:
    def __init__(self, regions: Optional[List[Region]] = None, failure_threshold: int = 3):
        self.regions: List[Region] = regions or []
        self._region_index: Dict[str, Region] = {r.region_id: r for r in self.regions}
        self.failure_threshold = failure_threshold
        self._active_region: Optional[str] = None
        self._failover_lock = False

    def register_region(self, region: Region) -> None:
        self.regions.append(region)
        self._region_index[region.region_id] = region
        logger.info("Registered region %s with endpoint %s", region.region_id, region.endpoint)

    def get_active_region(self) -> Optional[Region]:
        if self._active_region and self._active_region in self._region_index:
            region = self._region_index[self._active_region]
            if region.status == RegionStatus.HEALTHY:
                return region
        return self._select_best_region()

    def _select_best_region(self) -> Optional[Region]:
        healthy = [r for r in self.regions if r.status == RegionStatus.HEALTHY]
        if not healthy:
            return None
        healthy.sort(key=lambda r: (-r.priority, r.active_connections))
        best = healthy[0]
        self._active_region = best.region_id
        return best

    def report_failure(self, region_id: str) -> None:
        if region_id not in self._region_index:
            return
        region = self._region_index[region_id]
        region.failed_requests += 1
        if region.failed_requests >= self.failure_threshold:
            region.status = RegionStatus.UNAVAILABLE
            logger.warning("Region %s marked as unavailable after %d failures", region_id, region.failed_requests)
            if self._active_region == region_id:
                self._trigger_failover(region_id)

    def _trigger_failover(self, failed_region_id: str) -> None:
        if self._failover_lock:
            return
        self._failover_lock = True
        try:
            logger.info("Initiating failover from region %s", failed_region_id)
            failed_region = self._region_index[failed_region_id]
            failed_region.status = RegionStatus.FAILING_OVER
            new_active = self._select_best_region()
            if new_active:
                logger.info("Failover complete. New active region: %s", new_active.region_id)
                self._active_region = new_active.region_id
                failed_region.status = RegionStatus.UNAVAILABLE
            else:
                logger.error("No healthy regions available for failover")
        finally:
            self._failover_lock = False

    def perform_health_checks(self) -> Dict[str, RegionStatus]:
        results = {}
        for region in self.regions:
            healthy = self._check_region_health(region)
            if healthy:
                region.status = RegionStatus.HEALTHY
                region.failed_requests = 0
            else:
                region.failed_requests += 1
                if region.failed_requests >= self.failure_threshold:
                    region.status = RegionStatus.UNAVAILABLE
                else:
                    region.status = RegionStatus.DEGRADED
            results[region.region_id] = region.status
            region.last_health_check = datetime.utcnow()
        return results

    def _check_region_health(self, region: Region) -> bool:
        try:
            import requests
            response = requests.get(f"{region.endpoint}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_region_status(self) -> Dict[str, Any]:
        return {
            "active_region": self._active_region,
            "regions": [
                {
                    "region_id": r.region_id,
                    "endpoint": r.endpoint,
                    "status": r.status.value,
                    "priority": r.priority,
                    "active_connections": r.active_connections,
                    "failed_requests": r.failed_requests,
                }
                for r in self.regions
            ],
        }
