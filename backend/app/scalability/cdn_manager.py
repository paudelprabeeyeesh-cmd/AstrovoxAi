"""CDN manager for static asset distribution."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CDNConfig:
    cdn_id: str
    provider: str
    origins: List[str]
    ttl_seconds: int = 3600


class CDNManager:
    def __init__(self) -> None:
        self._configs: Dict[str, CDNConfig] = {}

    def create_config(self, config: CDNConfig) -> CDNConfig:
        self._configs[config.cdn_id] = config
        return config

    def purge(self, cdn_id: str, path: str) -> bool:
        return cdn_id in self._configs


cdn_manager = CDNManager()
