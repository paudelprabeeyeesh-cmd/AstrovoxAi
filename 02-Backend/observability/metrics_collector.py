import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional


class Counter:
    def __init__(self):
        self._values: Dict[str, int] = {}
        self._lock = threading.Lock()

    def inc(self, name: str, amount: int = 1):
        with self._lock:
            self._values[name] = self._values.get(name, 0) + amount

    def get(self, name: str) -> int:
        return self._values.get(name, 0)

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._values)


class Gauge:
    def __init__(self):
        self._values: Dict[str, float] = {}
        self._lock = threading.Lock()

    def set(self, name: str, value: float):
        with self._lock:
            self._values[name] = value

    def get(self, name: str) -> Optional[float]:
        return self._values.get(name)

    def snapshot(self) -> Dict[str, Optional[float]]:
        with self._lock:
            return dict(self._values)


class Histogram:
    def __init__(self):
        self._values: List[float] = []
        self._lock = threading.Lock()

    def record(self, value: float):
        with self._lock:
            self._values.append(value)

    def _percentile(self, values: List[float], p: float) -> Optional[float]:
        if not values:
            return None
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (p / 100.0)
        f = int(k)
        c = f + 1
        if c >= len(sorted_values):
            return sorted_values[f]
        d0 = sorted_values[f] * (c - k)
        d1 = sorted_values[c] * (k - f)
        return d0 + d1

    def p50(self) -> Optional[float]:
        with self._lock:
            values = list(self._values)
        return self._percentile(values, 50)

    def p95(self) -> Optional[float]:
        with self._lock:
            values = list(self._values)
        return self._percentile(values, 95)

    def p99(self) -> Optional[float]:
        with self._lock:
            values = list(self._values)
        return self._percentile(values, 99)

    def count(self) -> int:
        with self._lock:
            return len(self._values)

    def mean(self) -> Optional[float]:
        with self._lock:
            if not self._values:
                return None
            return sum(self._values) / len(self._values)

    def snapshot(self) -> Dict[str, Optional[float]]:
        with self._lock:
            values = list(self._values)
        return {
            "count": len(values),
            "mean": self.mean(),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
        }


class MetricsCollector:
    def __init__(self):
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()

    def counter(self, name: str) -> Counter:
        with self._lock:
            if name not in self.counters:
                self.counters[name] = Counter()
            return self.counters[name]

    def gauge(self, name: str) -> Gauge:
        with self._lock:
            if name not in self.gauges:
                self.gauges[name] = Gauge()
            return self.gauges[name]

    def histogram(self, name: str) -> Histogram:
        with self._lock:
            if name not in self.histograms:
                self.histograms[name] = Histogram()
            return self.histograms[name]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": {name: c.snapshot() for name, c in self.counters.items()},
                "gauges": {name: g.snapshot() for name, g in self.gauges.items()},
                "histograms": {name: h.snapshot() for name, h in self.histograms.items()},
            }
