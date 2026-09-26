"""Observability: structured logging, metrics, tracing."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Metric:
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """Collect and aggregate metrics."""

    def __init__(self) -> None:
        self._metrics: List[Metric] = []
        self._counters: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)

    def increment(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._make_key(name, labels)
        self._counters[key] += 1
        self._metrics.append(Metric(name=name, value=self._counters[key], labels=labels or {}))

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        self._metrics.append(Metric(name=name, value=value, labels=labels or {}))

    def get_summary(self, name: str) -> Dict[str, Any]:
        values = []
        for metric in self._metrics:
            if metric.name == name:
                values.append(metric.value)
        if not values:
            return {}
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    @staticmethod
    def _make_key(name: str, labels: Optional[Dict[str, str]]) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"


_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
