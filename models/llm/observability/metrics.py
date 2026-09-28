import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesPoint:
    timestamp: float
    value: float
    labels: dict[str, str] = field(default_factory=dict)


class TimeSeriesStore:
    def __init__(self, max_points: int = 10_000):
        self.max_points = max_points
        self._series: dict[str, deque[TimeSeriesPoint]] = {}

    def append(self, metric_name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self._make_key(metric_name, labels or {})
        if key not in self._series:
            self._series[key] = deque(maxlen=self.max_points)
        self._series[key].append(TimeSeriesPoint(timestamp=time.time(), value=value, labels=labels or {}))

    def get(self, metric_name: str, labels: dict[str, str] | None = None) -> deque[TimeSeriesPoint]:
        key = self._make_key(metric_name, labels or {})
        return self._series.get(key, deque())

    def query(
        self,
        metric_name: str,
        since: float | None = None,
        until: float | None = None,
        labels: dict[str, str] | None = None,
    ) -> list[TimeSeriesPoint]:
        points = self.get(metric_name, labels)
        result = list(points)
        if since is not None:
            result = [p for p in result if p.timestamp >= since]
        if until is not None:
            result = [p for p in result if p.timestamp <= until]
        return result

    def aggregate(self, metric_name: str, func: Callable[[list[float]], float], labels: dict[str, str] | None = None) -> float:
        points = self.get(metric_name, labels)
        values = [p.value for p in points]
        if not values:
            return 0.0
        return func(values)

    def _make_key(self, metric_name: str, labels: dict[str, str]) -> str:
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{metric_name}{{{label_str}}}"
        return metric_name

    def clear(self) -> None:
        self._series.clear()


class MetricsCollector:
    def __init__(self, store: TimeSeriesStore | None = None):
        self.store = store or TimeSeriesStore()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}

    def increment(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        key = self.store._make_key(name, labels or {})
        self._counters[key] = self._counters.get(key, 0.0) + value
        self.store.append(name, self._counters[key], labels)

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self.store._make_key(name, labels or {})
        self._gauges[key] = value
        self.store.append(name, value, labels)

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self.store.append(f"{name}_bucket", value, labels)

    def record(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        self.store.append(name, value, labels)

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        key = self.store._make_key(name, labels or {})
        return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        key = self.store._make_key(name, labels or {})
        return self._gauges.get(key, 0.0)

    def get_latest(self, name: str, labels: dict[str, str] | None = None) -> float | None:
        points = self.store.get(name, labels)
        if points:
            return points[-1].value
        return None
