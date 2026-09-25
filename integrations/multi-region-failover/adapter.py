import json
import time
import logging
import random
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class RegionHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class RegionEndpoint:
    region_id: str
    name: str
    base_url: str
    priority: int = 0
    weight: int = 1
    health: RegionHealth = RegionHealth.UNKNOWN
    last_health_check: Optional[str] = None
    consecutive_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailoverConfig:
    health_check_interval: int = 30
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2
    circuit_breaker_timeout: int = 60
    max_concurrent_checks: int = 5
    fallback_region: Optional[str] = None


class MultiRegionFailoverAdapter:
    def __init__(self, config: Optional[FailoverConfig] = None):
        self.config = config or FailoverConfig()
        self._regions: Dict[str, RegionEndpoint] = {}
        self._primary_region: Optional[str] = None
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_checks)
        self._circuit_breakers: Dict[str, datetime] = {}

    def register_region(self, region: RegionEndpoint):
        self._regions[region.region_id] = region
        if not self._primary_region or region.priority < self._regions[self._primary_region].priority:
            self._primary_region = region.region_id
        logger.info(f"Registered region {region.region_id} ({region.name}) with priority {region.priority}")

    def get_active_region(self) -> Optional[RegionEndpoint]:
        healthy_regions = [r for r in self._regions.values() if r.health == RegionHealth.HEALTHY]
        if not healthy_regions:
            fallback = self.config.fallback_region
            if fallback and fallback in self._regions:
                return self._regions[fallback]
            return None
        healthy_regions.sort(key=lambda r: (r.priority, -r.weight))
        return healthy_regions[0]

    def execute_with_failover(self, request_fn: Callable[[RegionEndpoint], Any]) -> Any:
        sorted_regions = sorted(self._regions.values(), key=lambda r: (r.priority, -r.weight))
        last_error = None
        for region in sorted_regions:
            if region.health == RegionHealth.UNHEALTHY:
                continue
            try:
                return request_fn(region)
            except Exception as e:
                last_error = e
                logger.warning(f"Region {region.region_id} failed: {e}")
                region.consecutive_failures += 1
                if region.consecutive_failures >= self.config.unhealthy_threshold:
                    region.health = RegionHealth.UNHEALTHY
                    self._circuit_breakers[region.region_id] = datetime.utcnow()
        if last_error:
            raise last_error
        raise RuntimeError("No healthy regions available")

    def run_health_checks(self) -> Dict[str, RegionHealth]:
        results = {}
        futures = {}
        for region_id, region in self._regions.items():
            futures[region_id] = self._executor.submit(self._check_region_health, region)
        for future in as_completed(futures):
            region_id, health = future.result()
            results[region_id] = health
        return results

    def _check_region_health(self, region: RegionEndpoint) -> tuple[str, RegionHealth]:
        try:
            if region.region_id in self._circuit_breakers:
                opened_at = self._circuit_breakers[region.region_id]
                if datetime.utcnow() > opened_at + timedelta(seconds=self.config.circuit_breaker_timeout):
                    del self._circuit_breakers[region.region_id]
                    region.health = RegionHealth.UNKNOWN
                    region.consecutive_failures = 0
            start = time.time()
            response = __import__('requests').get(f"{region.base_url}/health", timeout=5)
            latency = (time.time() - start) * 1000
            if response.status_code == 200 and latency < 1000:
                region.health = RegionHealth.HEALTHY
                region.consecutive_failures = 0
            else:
                region.consecutive_failures += 1
                region.health = RegionHealth.DEGRADED if region.consecutive_failures < self.config.unhealthy_threshold else RegionHealth.UNHEALTHY
            region.last_health_check = datetime.utcnow().isoformat()
        except Exception as e:
            region.consecutive_failures += 1
            region.health = RegionHealth.DEGRADED if region.consecutive_failures < self.config.unhealthy_threshold else RegionHealth.UNHEALTHY
            region.last_health_check = datetime.utcnow().isoformat()
            logger.warning(f"Health check failed for region {region.region_id}: {e}")
        return region.region_id, region.health

    def get_region_status(self) -> List[Dict[str, Any]]:
        return [
            {"region_id": r.region_id, "name": r.name, "health": r.health.value, "priority": r.priority, "last_check": r.last_health_check, "failures": r.consecutive_failures}
            for r in sorted(self._regions.values(), key=lambda r: r.priority)
        ]

    def promote_region(self, region_id: str):
        region = self._regions.get(region_id)
        if not region:
            raise ValueError(f"Region {region_id} not found")
        region.priority = 0
        region.health = RegionHealth.HEALTHY
        region.consecutive_failures = 0
        self._primary_region = region_id
        logger.info(f"Promoted region {region_id} to primary")

    def drain_region(self, region_id: str):
        region = self._regions.get(region_id)
        if not region:
            raise ValueError(f"Region {region_id} not found")
        region.health = RegionHealth.UNHEALTHY
        logger.info(f"Drained region {region_id}")

    def shutdown(self):
        self._executor.shutdown(wait=False)
