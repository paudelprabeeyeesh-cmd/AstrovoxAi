"""Cloud-init configuration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CloudInitConfig:
    config_id: str
    user_data: str
    meta_data: Dict[str, Any] = field(default_factory=dict)
    network_config: Dict[str, Any] = field(default_factory=dict)


class CloudInitManager:
    def __init__(self) -> None:
        self._configs: Dict[str, CloudInitConfig] = {}

    def create_config(self, config: CloudInitConfig) -> CloudInitConfig:
        self._configs[config.config_id] = config
        return config


cloud_init_manager = CloudInitManager()
