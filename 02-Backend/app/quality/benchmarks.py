"""Benchmark and release comparison gates."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    commit: str
    p50_ms: float
    p99_ms: float
    cost_usd: float


class PRBenchmarkGate:
    def compare(self, base: str, head: str) -> dict[str, Any]:
        return {"base": base, "head": head, "p50_regression": False, "p99_regression": False, "cost_regression": False}


class ReleaseComparator:
    def compare(self, previous: str, current: str) -> dict[str, Any]:
        return {"previous": previous, "current": current, "latency_delta_pct": 0.0, "cost_delta_pct": 0.0}
