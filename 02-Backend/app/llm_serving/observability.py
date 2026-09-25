"""Observability hooks for latency, throughput, token usage, and serving metrics."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    request_id: str
    model: str
    tenant_id: Optional[str]
    user_id: Optional[str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    queue_time_ms: float = 0.0
    time_to_first_token_ms: float = 0.0
    status: str = "pending"
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


class ObservabilityHooks:
    def __init__(self, max_history: int = 10000):
        self._max_history = max_history
        self._metrics: dict[str, RequestMetrics] = {}
        self._lock = Lock()
        self._total_requests = 0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._latency_sum = 0.0
        self._latency_sq_sum = 0.0
        self._error_count = 0

    def record_request_start(self, request_id: str, model: str, tenant_id: Optional[str] = None, user_id: Optional[str] = None) -> RequestMetrics:
        with self._lock:
            metrics = RequestMetrics(
                request_id=request_id,
                model=model,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            self._metrics[request_id] = metrics
            self._total_requests += 1
            return metrics

    def record_request_end(self, request_id: str, status: str, error: Optional[str] = None) -> Optional[RequestMetrics]:
        with self._lock:
            metrics = self._metrics.get(request_id)
            if not metrics:
                return None
            metrics.status = status
            metrics.error = error
            metrics.finished_at = time.time()
            metrics.total_tokens = metrics.prompt_tokens + metrics.completion_tokens
            if metrics.started_at:
                metrics.latency_ms = (metrics.finished_at - metrics.started_at) * 1000
                metrics.queue_time_ms = (metrics.started_at - metrics.created_at) * 1000
                self._latency_sum += metrics.latency_ms
                self._latency_sq_sum += metrics.latency_ms ** 2
            self._total_prompt_tokens += metrics.prompt_tokens
            self._total_completion_tokens += metrics.completion_tokens
            if status == "error":
                self._error_count += 1
            self._trim_history()
            return metrics

    def record_tokens(self, request_id: str, prompt_tokens: int, completion_tokens: int) -> None:
        with self._lock:
            metrics = self._metrics.get(request_id)
            if metrics:
                metrics.prompt_tokens += prompt_tokens
                metrics.completion_tokens += completion_tokens

    def record_time_to_first_token(self, request_id: str, ttft_ms: float) -> None:
        with self._lock:
            metrics = self._metrics.get(request_id)
            if metrics:
                metrics.time_to_first_token_ms = ttft_ms

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            n = self._total_requests
            mean_latency = self._latency_sum / n if n > 0 else 0.0
            variance = (self._latency_sq_sum / n - mean_latency ** 2) if n > 0 else 0.0
            return {
                "total_requests": n,
                "total_prompt_tokens": self._total_prompt_tokens,
                "total_completion_tokens": self._total_completion_tokens,
                "total_tokens": self._total_prompt_tokens + self._total_completion_tokens,
                "error_count": self._error_count,
                "error_rate": self._error_count / n if n > 0 else 0.0,
                "mean_latency_ms": mean_latency,
                "latency_variance": variance,
                "active_requests": len([m for m in self._metrics.values() if m.status == "running"]),
            }

    def get_request(self, request_id: str) -> Optional[RequestMetrics]:
        with self._lock:
            return self._metrics.get(request_id)

    def _trim_history(self) -> None:
        if len(self._metrics) > self._max_history:
            oldest = sorted(self._metrics.items(), key=lambda x: x[1].created_at)
            remove_count = len(self._metrics) - self._max_history
            for key, _ in oldest[:remove_count]:
                del self._metrics[key]


class LatencyTracker:
    def __init__(self, window_size: int = 1000):
        self._window_size = window_size
        self._latencies: list[float] = []
        self._lock = Lock()

    def record(self, latency_ms: float) -> None:
        with self._lock:
            self._latencies.append(latency_ms)
            if len(self._latencies) > self._window_size:
                self._latencies.pop(0)

    def stats(self) -> dict[str, float]:
        with self._lock:
            if not self._latencies:
                return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0, "max": 0.0}
            sorted_latencies = sorted(self._latencies)
            n = len(sorted_latencies)
            return {
                "p50": sorted_latencies[int(n * 0.5)],
                "p95": sorted_latencies[int(n * 0.95)],
                "p99": sorted_latencies[int(n * 0.99)],
                "mean": sum(sorted_latencies) / n,
                "max": sorted_latencies[-1],
            }


class ThroughputTracker:
    def __init__(self, window_seconds: float = 60.0):
        self._window = window_seconds
        self._timestamps: list[float] = []
        self._lock = Lock()

    def record(self, tokens: int = 0) -> None:
        now = time.time()
        with self._lock:
            self._timestamps.append((now, tokens))
            cutoff = now - self._window
            self._timestamps = [(t, tok) for t, tok in self._timestamps if t >= cutoff]

    def throughput_per_second(self) -> float:
        now = time.time()
        with self._lock:
            cutoff = now - self._window
            recent = [tok for t, tok in self._timestamps if t >= cutoff]
            elapsed = min(self._window, now - self._timestamps[0][0]) if self._timestamps else self._window
            return sum(recent) / max(elapsed, 0.001)

    def requests_per_second(self) -> float:
        now = time.time()
        with self._lock:
            cutoff = now - self._window
            recent = [t for t, _ in self._timestamps if t >= cutoff]
            elapsed = min(self._window, now - recent[0]) if recent else self._window
            return len(recent) / max(elapsed, 0.001)
