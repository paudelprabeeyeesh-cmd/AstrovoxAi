"""AI telemetry collector."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class AITelemetryCollector:
    service: str = "astrovox-ai"

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        logger.debug("metric %s=%f %s", name, value, labels or {})

    def record_latency(self, operation: str, duration_ms: float) -> None:
        self.record_metric(f"{operation}_latency_ms", duration_ms)


ai_telemetry_collector = AITelemetryCollector()
