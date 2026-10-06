"""Usage statistics and metrics collection."""

from __future__ import annotations

import time


class UsageStats:
    """Usage statistics collector."""

    def __init__(self):
        self.metrics: dict[str, float] = {}
        self.start_time = time.time()
        self.calls: dict[str, int] = {}

    def record_call(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1

    def gauge(self, name: str, value: float) -> None:
        self.metrics[name] = value

    def histogram(self, name: str, value: float) -> None:
        self.metrics.setdefault(name + "_count", 0)
        self.metrics[name + "_sum"] = self.metrics.get(name + "_sum", 0) + value
        self.metrics[name + "_count"] = self.metrics.get(name + "_count", 0) + 1

    def get(self, name: str, default: float = 0.0) -> float:
        return self.metrics.get(name, default)

    def summary(self) -> dict:
        return {"uptime_seconds": time.time() - self.start_time,
                "metric_count": len(self.metrics), "call_count": sum(self.calls.values()),
                "calls": dict(self.calls)}

    def reset(self) -> None:
        self.metrics.clear()
        self.calls.clear()
        self.start_time = time.time()
