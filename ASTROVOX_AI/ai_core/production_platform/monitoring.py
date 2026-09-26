"""AI monitoring."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIHealthCheck:
    model_id: str
    healthy: bool
    latency_ms: float
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AIMonitoring:
    def __init__(self) -> None:
        self._health: Dict[str, AIHealthCheck] = {}

    def check_health(self, model_id: str, latency_ms: float) -> AIHealthCheck:
        healthy = latency_ms < 1000.0
        check = AIHealthCheck(model_id=model_id, healthy=healthy, latency_ms=latency_ms)
        self._health[model_id] = check
        return check

    def get_health(self, model_id: str) -> Optional[AIHealthCheck]:
        return self._health.get(model_id)


ai_monitoring = AIMonitoring()
