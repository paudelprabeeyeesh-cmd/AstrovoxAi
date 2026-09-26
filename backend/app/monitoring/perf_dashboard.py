"""Performance dashboard data aggregation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List


@dataclass
class PerfSample:
    timestamp: datetime
    latency_p50: float
    latency_p95: float
    latency_p99: float
    throughput_rps: float
    error_rate: float
    cpu_percent: float
    memory_percent: float


class PerfDashboard:
    def __init__(self, max_samples: int = 1000) -> None:
        self._samples: List[PerfSample] = []
        self._max_samples = max_samples

    def record(self, sample: PerfSample) -> None:
        self._samples.append(sample)
        if len(self._samples) > self._max_samples:
            self._samples = self._samples[-self._max_samples :]

    def latest(self) -> Dict[str, float]:
        if not self._samples:
            return {}
        s = self._samples[-1]
        return {
            "latency_p50": s.latency_p50,
            "latency_p95": s.latency_p95,
            "latency_p99": s.latency_p99,
            "throughput_rps": s.throughput_rps,
            "error_rate": s.error_rate,
            "cpu_percent": s.cpu_percent,
            "memory_percent": s.memory_percent,
        }

    def history(self) -> List[Dict[str, float]]:
        result = []
        for s in self._samples:
            result.append(
                {
                    "timestamp": s.timestamp.isoformat(),
                    "latency_p50": s.latency_p50,
                    "latency_p95": s.latency_p95,
                    "latency_p99": s.latency_p99,
                    "throughput_rps": s.throughput_rps,
                    "error_rate": s.error_rate,
                    "cpu_percent": s.cpu_percent,
                    "memory_percent": s.memory_percent,
                }
            )
        return result
