"""Capacity planning and forecasting."""
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class CapacityMetric:
    resource: str
    current_usage: float
    peak_usage: float
    limit: float
    unit: str


class CapacityPlanner:
    def __init__(self):
        self._metrics: Dict[str, CapacityMetric] = {}
        self._history: List[Dict[str, float]] = []

    def record(self, metric: CapacityMetric):
        self._metrics[metric.resource] = metric
        self._history.append({
            "resource": metric.resource,
            "current": metric.current_usage,
            "peak": metric.peak_usage,
            "limit": metric.limit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def utilization(self, resource: str) -> float:
        metric = self._metrics.get(resource)
        if not metric or metric.limit == 0:
            return 0.0
        return metric.current_usage / metric.limit

    def forecast(self, resource: str, growth_rate: float = 0.1) -> Optional[float]:
        metric = self._metrics.get(resource)
        if not metric:
            return None
        projected = metric.current_usage * (1.0 + growth_rate)
        return projected

    def recommendation(self) -> List[str]:
        recommendations = []
        for name, metric in self._metrics.items():
            util = self.utilization(name)
            if util >= 0.8:
                recommendations.append(f"Increase capacity for {name}: current utilization {util:.0%}")
            forecast = self.forecast(name)
            if forecast and forecast > metric.limit:
                recommendations.append(
                    f"Projected capacity breach for {name}: forecast {forecast:.2f} {metric.unit} exceeds limit {metric.limit:.2f} {metric.unit}"
                )
        return recommendations
