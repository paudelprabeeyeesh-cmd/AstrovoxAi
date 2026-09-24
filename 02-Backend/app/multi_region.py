"""Multi-region support for AstrovoxAI backend.

Provides region-aware routing, data residency, and cross-region replication.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RegionStrategy(str, Enum):
    LATENCY = "latency"
    GEOGRAPHIC = "geographic"
    WEIGHTED = "weighted"
    FAILOVER = "failover"


@dataclass(frozen=True)
class RegionConfig:
    name: str
    code: str
    provider: str
    primary: bool = False
    postgres_uri: str = ""
    redis_uri: str = ""
    vector_db_uri: str = ""
    cdn_endpoint: str = ""
    weight: int = 1
    allowed_data_residency: List[str] | None = None

    def __post_init__(self) -> None:
        if self.allowed_data_residency is None:
            object.__setattr__(self, "allowed_data_residency", [])


MULTI_REGION_CONFIG: Dict[str, RegionConfig] = {
    "us-east-1": RegionConfig(
        name="US East",
        code="us-east-1",
        provider="aws",
        primary=True,
        postgres_uri=os.getenv("PRIMARY_POSTGRES_URI", ""),
        redis_uri=os.getenv("PRIMARY_REDIS_URI", "redis://redis.us-east-1:6379"),
        vector_db_uri=os.getenv("PRIMARY_VECTOR_URI", ""),
        cdn_endpoint=os.getenv("CDN_US_EAST", ""),
        weight=10,
        allowed_data_residency=["US", "CA", "MX"],
    ),
    "eu-west-1": RegionConfig(
        name="EU West",
        code="eu-west-1",
        provider="aws",
        postgres_uri=os.getenv("REPLICA_POSTGRES_URI_EU", ""),
        redis_uri=os.getenv("REPLICA_REDIS_URI_EU", "redis://redis.eu-west-1:6379"),
        vector_db_uri=os.getenv("REPLICA_VECTOR_URI_EU", ""),
        cdn_endpoint=os.getenv("CDN_EU_WEST", ""),
        weight=8,
        allowed_data_residency=["GB", "DE", "FR", "IE", "NL"],
    ),
    "ap-south-1": RegionConfig(
        name="Asia Pacific",
        code="ap-south-1",
        provider="aws",
        postgres_uri=os.getenv("REPLICA_POSTGRES_URI_AP", ""),
        redis_uri=os.getenv("REPLICA_REDIS_URI_AP", "redis://redis.ap-south-1:6379"),
        vector_db_uri=os.getenv("REPLICA_VECTOR_URI_AP", ""),
        cdn_endpoint=os.getenv("CDN_AP_SOUTH", ""),
        weight=5,
        allowed_data_residency=["IN", "SG", "AU", "JP"],
    ),
}


class MultiRegionManager:
    """Manages multi-region routing and failover."""

    def __init__(self, strategy: RegionStrategy = RegionStrategy.LATENCY):
        self.strategy = strategy
        self._regions = dict(MULTI_REGION_CONFIG)
        self._primary_region: Optional[RegionConfig] = None
        for region in self._regions.values():
            if region.primary:
                self._primary_region = region
                break

    def get_region(self, name: str) -> Optional[RegionConfig]:
        return self._regions.get(name)

    def get_primary_region(self) -> Optional[RegionConfig]:
        return self._primary_region

    def get_regions(self) -> List[RegionConfig]:
        return list(self._regions.values())

    def resolve_region(self, user_country: str = "", latency_ms: Dict[str, float] | None = None) -> RegionConfig:
        if self.strategy == RegionStrategy.FAILOVER and self._primary_region:
            return self._primary_region
        if self.strategy == RegionStrategy.LATENCY and latency_ms:
            return min(self._regions.values(), key=lambda r: latency_ms.get(r.code, float("inf")))
        if self.strategy == RegionStrategy.GEOGRAPHIC:
            for region in self._regions.values():
                if user_country.upper() in [c.upper() for c in region.allowed_data_residency]:
                    return region
        if self.strategy == RegionStrategy.WEIGHTED:
            import random
            return random.choices(list(self._regions.values()), weights=[r.weight for r in self._regions.values()], k=1)[0]
        return self._primary_region or list(self._regions.values())[0]

    def get_failover_region(self, failed_region: str) -> Optional[RegionConfig]:
        for region in self._regions.values():
            if region.code != failed_region and region.healthy:
                return region
        return None

    def is_healthy(self, region_name: str) -> bool:
        region = self._regions.get(region_name)
        return region.healthy if region else False


multi_region_manager = MultiRegionManager()
