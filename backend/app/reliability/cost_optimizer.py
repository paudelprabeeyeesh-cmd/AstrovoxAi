"""Cost optimization analysis."""
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class CostMetric:
    service: str
    daily_cost_usd: float
    monthly_estimate_usd: float
    optimization_suggestion: str


class CostOptimizer:
    def __init__(self):
        self._metrics: Dict[str, CostMetric] = {}
        self._last_updated = datetime.now(timezone.utc)

    def register(self, service: str, daily_cost: float, suggestion: str = ""):
        monthly = daily_cost * 30.0
        self._metrics[service] = CostMetric(
            service=service,
            daily_cost_usd=daily_cost,
            monthly_estimate_usd=monthly,
            optimization_suggestion=suggestion,
        )
        self._last_updated = datetime.now(timezone.utc)

    def total_monthly_estimate(self) -> float:
        return sum(m.monthly_estimate_usd for m in self._metrics.values())

    def suggestions(self) -> List[str]:
        return [m.optimization_suggestion for m in self._metrics.values() if m.optimization_suggestion]

    def report(self) -> Dict[str, Dict[str, float]]:
        return {
            name: {
                "daily_cost_usd": m.daily_cost_usd,
                "monthly_estimate_usd": m.monthly_estimate_usd,
            }
            for name, m in self._metrics.items()
        }
