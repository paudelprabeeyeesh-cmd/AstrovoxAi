"""AI global deployment manager."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIRegionConfig:
    region: str
    provider: str
    enabled: bool = True
    endpoints: List[str] = field(default_factory=list)


class AIGlobalDeploymentManager:
    def __init__(self) -> None:
        self._regions: Dict[str, AIRegionConfig] = {}

    def add_region(self, config: AIRegionConfig) -> None:
        self._regions[config.region] = config

    def list_regions(self) -> List[AIRegionConfig]:
        return list(self._regions.values())


ai_global_deployment_manager = AIGlobalDeploymentManager()
