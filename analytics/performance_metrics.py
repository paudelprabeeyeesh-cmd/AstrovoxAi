"""
Performance metrics for AstrovoxAI.
Tracks latency, throughput, error rates, and system health.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LatencyStats:
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean_ms": self.mean_ms,
            "median_ms": self.median_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
        }


@dataclass
class ThroughputStats:
    requests_per_second: float
    requests_per_minute: float
    tokens_per_second: float
    peak_rps: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_per_second": self.requests_per_second,
            "requests_per_minute": self.requests_per_minute,
            "tokens_per_second": self.tokens_per_second,
            "peak_rps": self.peak_rps,
        }


class PerformanceMetrics:
    """Collects and aggregates performance metrics."""

    def __init__(self):
        self._latency_samples: List[float] = []
        self._throughput_samples: List[Dict[str, Any]] = []
        self._error_counts: Dict[str, int] = {}
        self._request_timestamps: List[float] = []

    def record_latency(self, latency_ms: float) -> None:
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > 10000:
            self._latency_samples = self._latency_samples[-5000:]

    def record_request(self, endpoint: str, tokens: int = 0) -> None:
        now = time.time()
        self._request_timestamps.append(now)
        self._request_timestamps = [
            ts for ts in self._request_timestamps if now - ts <= 60
        ]

    def record_error(self, error_type: str) -> None:
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

    def get_latency_stats(self, window_minutes: int = 60) -> LatencyStats:
        samples = self._latency_samples
        if not samples:
            return LatencyStats(0, 0, 0, 0, 0, 0)
        samples = sorted(samples)
        n = len(samples)
        return LatencyStats(
            mean_ms=sum(samples) / n,
            median_ms=samples[n // 2],
            p95_ms=samples[int(n * 0.95)],
            p99_ms=samples[int(n * 0.99)],
            min_ms=min(samples),
            max_ms=max(samples),
        )

    def get_throughput_stats(self, window_seconds: int = 60) -> ThroughputStats:
        now = time.time()
        recent = [ts for ts in self._request_timestamps if now - ts <= window_seconds]
        rps = len(recent) / window_seconds if window_seconds > 0 else 0
        return ThroughputStats(
            requests_per_second=rps,
            requests_per_minute=rps * 60,
            tokens_per_second=0.0,
            peak_rps=max(rps, 0.0),
        )

    def get_error_rate(self, window_minutes: int = 60) -> float:
        total_errors = sum(self._error_counts.values())
        total_requests = len(self._request_timestamps)
        if total_requests == 0:
            return 0.0
        return total_errors / total_requests
