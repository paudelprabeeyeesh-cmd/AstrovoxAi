"""Carbon footprint tracking for AI workloads."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CarbonFootprint:
    service: str
    energy_kwh: float
    carbon_g: float
    region: str
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CarbonTracker:
    def __init__(self) -> None:
        self._records: List[CarbonFootprint] = []

    def record(self, service: str, energy_kwh: float, region: str = "us-east-1") -> CarbonFootprint:
        carbon_g = energy_kwh * 400.0
        record = CarbonFootprint(service=service, energy_kwh=energy_kwh, carbon_g=carbon_g, region=region)
        self._records.append(record)
        return record

    def get_footprint(self, service: Optional[str] = None) -> List[CarbonFootprint]:
        if service:
            return [r for r in self._records if r.service == service]
        return list(self._records)


carbon_tracker = CarbonTracker()
