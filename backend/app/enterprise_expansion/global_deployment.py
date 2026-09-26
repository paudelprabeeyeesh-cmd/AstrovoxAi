"""Global deployment management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RegionConfig:
    region: str
    provider: str
    enabled: bool = True
    endpoints: List[str] = field(default_factory=list)


class GlobalDeploymentManager:
    def __init__(self) -> None:
        self._regions: Dict[str, RegionConfig] = {}

    def add_region(self, config: RegionConfig) -> None:
        self._regions[config.region] = config

    def list_regions(self) -> List[RegionConfig]:
        return list(self._regions.values())

    def get_region(self, region: str) -> Optional[RegionConfig]:
        return self._regions.get(region)


global_deployment_manager = GlobalDeploymentManager()
