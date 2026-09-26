"""Canary release orchestration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class CanaryConfig:
    service_name: str
    stable_image: str
    canary_image: str
    traffic_percent: float = 0.1
    duration_seconds: int = 300
    success_threshold: float = 0.99


class CanaryRelease:
    def __init__(self, config: CanaryConfig) -> None:
        self.config = config
        self.status = "running"
        self.started_at = datetime.now(timezone.utc)

    async def promote(self) -> Dict[str, Any]:
        self.status = "completed"
        return {
            "service": self.config.service_name,
            "status": self.status,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
        }

    async def abort(self, reason: str) -> Dict[str, Any]:
        self.status = "aborted"
        return {
            "service": self.config.service_name,
            "status": self.status,
            "reason": reason,
            "aborted_at": datetime.now(timezone.utc).isoformat(),
        }
