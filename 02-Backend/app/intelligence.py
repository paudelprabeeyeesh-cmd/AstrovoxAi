"""Business Intelligence — dashboards, forecasting, KPI tracking."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KPI:
    """A Key Performance Indicator."""
    id: str
    name: str
    value: float
    target: float
    unit: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()

    @property
    def progress(self) -> float:
        if self.target == 0:
            return 100.0
        return min(100.0, (self.value / self.target) * 100)


class BusinessIntelligence:
    """Business intelligence platform."""

    def __init__(self):
        self._kpis: dict[str, KPI] = {}
        self._reports: list = []

    def add_kpi(self, name: str, value: float, target: float, unit: str = "") -> KPI:
        """Add a KPI."""
        import secrets
        kpi = KPI(
            id=secrets.token_hex(8),
            name=name,
            value=value,
            target=target,
            unit=unit,
        )
        self._kpis[kpi.id] = kpi
        return kpi

    def update_kpi(self, kpi_id: str, value: float):
        kpi = self._kpis.get(kpi_id)
        if kpi:
            kpi.value = value
            kpi.timestamp = time.time()

    def get_kpis(self) -> list:
        return list(self._kpis.values())

    def generate_report(self) -> dict:
        """Generate a business report."""
        return {
            "timestamp": time.time(),
            "kpis": [
                {
                    "name": k.name,
                    "value": k.value,
                    "target": k.target,
                    "progress": k.progress,
                }
                for k in self._kpis.values()
            ],
        }


business_intel = BusinessIntelligence()
