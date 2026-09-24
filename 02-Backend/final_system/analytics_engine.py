"""
Analytics engine with metrics, aggregations, and insights.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class Metric:
    name: str
    values: List[float] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)


AggregationFn = Callable[[List[float]], float]


class AnalyticsEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._metrics: Dict[str, Metric] = {}

    def add_metric(self, metric: Metric) -> None:
        with self._lock:
            self._metrics[metric.name] = metric

    def record(self, name: str, value: float) -> None:
        with self._lock:
            metric = self._metrics.get(name)
            if metric:
                metric.values.append(value)

    def aggregate(self, name: str, fn: AggregationFn) -> Optional[float]:
        with self._lock:
            metric = self._metrics.get(name)
        if not metric or not metric.values:
            return None
        return fn(metric.values)

    def insight(self, name: str) -> Dict[str, Optional[float]]:
        with self._lock:
            metric = self._metrics.get(name)
        if not metric or not metric.values:
            return {"mean": None, "min": None, "max": None, "count": 0}
        values = metric.values
        return {
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }

    def list_metrics(self) -> List[str]:
        with self._lock:
            return list(self._metrics.keys())
