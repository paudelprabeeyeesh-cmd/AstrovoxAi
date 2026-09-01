"""Global Infrastructure — multi-region, CDN, edge computing."""

import time
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Region:
    """A deployment region."""
    id: str
    name: str
    location: str
    is_active: bool = True
    latency_ms: float = 0.0


class GlobalInfrastructure:
    """Manage global infrastructure."""

    def __init__(self):
        self._regions: dict[str, Region] = {}

    def add_region(self, region: Region):
        """Add a region."""
        self._regions[region.id] = region

    def get_closest_region(self, user_lat: float, user_lon: float) -> Optional[Region]:
        """Get closest region to user."""
        active = [r for r in self._regions.values() if r.is_active]
        if not active:
            return None
        return min(active, key=lambda r: r.latency_ms)

    def get_all_regions(self) -> list:
        return list(self._regions.values())


global_infra = GlobalInfrastructure()
