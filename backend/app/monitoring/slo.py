"""SLO/SLA tracking."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class SLO:
    name: str
    target: float
    window_days: int = 30
    unit: str = "ratio"

    def evaluate(self, good: float, total: float) -> Dict[str, float]:
        if total <= 0:
            return {"ratio": 0.0, "target": self.target, "achieved": False, "remaining": 0.0}
        ratio = good / total
        error_budget = 1.0 - self.target
        consumed = 1.0 - ratio
        remaining = max(0.0, error_budget - consumed)
        return {
            "ratio": ratio,
            "target": self.target,
            "achieved": ratio >= self.target,
            "remaining": remaining,
        }


class SLOTracker:
    def __init__(self):
        self._slos: Dict[str, SLO] = {
            "availability": SLO("availability", 0.99, window_days=30),
            "latency_p95": SLO("latency_p95", 0.95, window_days=30),
            "error_rate": SLO("error_rate", 0.999, window_days=30),
        }
        self._counters: Dict[str, Dict[str, float]] = {
            "availability": {"good": 0.0, "total": 0.0},
            "latency_p95": {"good": 0.0, "total": 0.0},
            "error_rate": {"good": 0.0, "total": 0.0},
        }

    def record(self, slo_name: str, good: bool, count: float = 1.0):
        if slo_name not in self._counters:
            raise KeyError(f"Unknown SLO: {slo_name}")
        self._counters[slo_name]["total"] += count
        if good:
            self._counters[slo_name]["good"] += count

    def evaluate(self, slo_name: str) -> Dict[str, float]:
        if slo_name not in self._slos:
            raise KeyError(f"Unknown SLO: {slo_name}")
        counters = self._counters[slo_name]
        return self._slos[slo_name].evaluate(counters["good"], counters["total"])

    def all_statuses(self) -> Dict[str, Dict[str, float]]:
        return {name: self.evaluate(name) for name in self._slos}
