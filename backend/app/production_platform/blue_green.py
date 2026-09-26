"""Blue-green deployment support."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class BlueGreenConfig:
    service_name: str
    blue_image: str
    green_image: str
    active_color: str = "blue"


class BlueGreenDeployment:
    def __init__(self, config: BlueGreenConfig) -> None:
        self.config = config
        self.active_color = config.active_color
        self.status = "ready"

    async def switch(self, target_color: str) -> Dict[str, Any]:
        self.active_color = target_color
        self.status = "active"
        return {
            "service": self.config.service_name,
            "active_color": target_color,
            "switched_at": datetime.now(timezone.utc).isoformat(),
        }

    async def validate(self) -> Dict[str, Any]:
        return {
            "service": self.config.service_name,
            "active_color": self.active_color,
            "status": self.status,
            "healthy": True,
        }
