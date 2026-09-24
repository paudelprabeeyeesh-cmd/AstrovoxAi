import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class RegionState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class Region:
    name: str
    endpoint: str
    state: RegionState = RegionState.HEALTHY
    rto_seconds: float = 30.0
    rpo_seconds: float = 5.0


class DisasterRecoveryManager:
    def __init__(self, primary_region: str, regions: List[Region]) -> None:
        self._primary = primary_region
        self._regions = {r.name: r for r in regions}
        self._active_region = primary_region
        self._lock = threading.Lock()

    def health_check(self, region: str) -> bool:
        r = self._regions.get(region)
        if r is None:
            return False
        r.state = RegionState.HEALTHY if r.state != RegionState.FAILED else RegionState.DEGRADED
        return r.state != RegionState.FAILED

    def failover(self, target: str) -> Dict[str, Any]:
        with self._lock:
            if target not in self._regions:
                raise ValueError("Unknown region")
            self._active_region = target
            self._regions[target].state = RegionState.HEALTHY
            return {
                "previous_primary": self._primary,
                "new_primary": target,
                "timestamp": time.time(),
                "rto": self._regions[target].rto_seconds,
                "rpo": self._regions[target].rpo_seconds,
            }

    def active_region(self) -> str:
        return self._active_region

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "primary": self._primary,
                "active": self._active_region,
                "regions": {name: r.state.value for name, r in self._regions.items()},
            }
