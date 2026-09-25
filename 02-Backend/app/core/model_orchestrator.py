"""
Model orchestrator with dynamic selection, circuit breaker, fallback, and metrics.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .model_router_core import ModelRouter, ModelEndpoint

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationRequest:
    request_id: str
    capabilities: List[str]
    max_context: int
    budget_per_1k: Optional[float] = None
    latency_target_ms: Optional[float] = None
    quality_target: Optional[float] = None
    preferred_provider: Optional[str] = None
    retries: int = 3
    timeout_ms: float = 30_000.0


@dataclass
class OrchestrationResult:
    request_id: str
    provider: str
    model: str
    latency_ms: float
    tokens_used: int
    success: bool
    error: Optional[str] = None
    fallback_used: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CircuitBreaker:
    """Simple circuit breaker for model endpoints."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures: Dict[str, int] = {}
        self.last_failure_time: Dict[str, float] = {}
        self.lock = threading.Lock()

    def allow_request(self, model_name: str) -> bool:
        with self.lock:
            failures = self.failures.get(model_name, 0)
            if failures >= self.failure_threshold:
                last_failure = self.last_failure_time.get(model_name, 0.0)
                if time.time() - last_failure < self.recovery_timeout:
                    return False
                self.failures[model_name] = 0
                return True
            return True

    def record_success(self, model_name: str):
        with self.lock:
            self.failures[model_name] = 0

    def record_failure(self, model_name: str):
        with self.lock:
            self.failures[model_name] = self.failures.get(model_name, 0) + 1
            self.last_failure_time[model_name] = time.time()

    def reset(self, model_name: str):
        with self.lock:
            self.failures[model_name] = 0


class ModelOrchestrator:
    """Orchestrates requests across models with dynamic selection, circuit breaker, fallback, and metrics."""

    def __init__(self, router: Optional[ModelRouter] = None):
        self.router = router or ModelRouter()
        self.circuit_breaker = CircuitBreaker()
        self.history: List[OrchestrationResult] = []
        self.lock = threading.Lock()

    def register_endpoint(self, endpoint: ModelEndpoint):
        self.router.register_endpoint(endpoint)

    def set_fallback_chain(self, chain: List[str]):
        self.router.set_fallback_chain(chain)

    def _score_candidate(self, endpoint: ModelEndpoint, request: OrchestrationRequest) -> float:
        score = (1.0 / (endpoint.latency_ms + 1.0)) * (1.0 - endpoint.error_rate) * endpoint.priority
        if request.budget_per_1k is not None and endpoint.cost_per_1k_tokens > request.budget_per_1k:
            score *= 0.1
        if request.latency_target_ms is not None and endpoint.latency_ms > request.latency_target_ms:
            score *= 0.5
        if request.quality_target is not None and endpoint.error_rate > (1.0 - request.quality_target):
            score *= 0.5
        if request.preferred_provider and endpoint.provider == request.preferred_provider:
            score *= 1.5
        return score

    def _select_endpoint(self, request: OrchestrationRequest) -> Optional[ModelEndpoint]:
        candidates = []
        for endpoint in self.router.endpoints.values():
            if not all(cap in endpoint.capabilities for cap in request.capabilities):
                continue
            if request.max_context > endpoint.max_context:
                continue
            if not self.circuit_breaker.allow_request(endpoint.name):
                continue
            candidates.append((self._score_candidate(endpoint, request), endpoint))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def _execute_with_fallback(self, request: OrchestrationRequest, runner) -> OrchestrationResult:
        last_error: Optional[str] = None
        attempts = 0
        current_endpoint = self._select_endpoint(request)
        while attempts < max(request.retries, 1):
            if current_endpoint is None:
                break
            attempts += 1
            start = time.perf_counter()
            try:
                result = runner(current_endpoint)
                latency = (time.perf_counter() - start) * 1000.0
                self.circuit_breaker.record_success(current_endpoint.name)
                self.router.record_request(current_endpoint.name, True, latency)
                return OrchestrationResult(
                    request_id=request.request_id,
                    provider=current_endpoint.provider,
                    model=current_endpoint.model_id,
                    latency_ms=latency,
                    tokens_used=result.get("tokens", 0),
                    success=True,
                    fallback_used=attempts > 1,
                )
            except Exception as exc:
                latency = (time.perf_counter() - start) * 1000.0
                last_error = str(exc)
                self.circuit_breaker.record_failure(current_endpoint.name)
                self.router.record_request(current_endpoint.name, False, latency)
                fallback = self.router.get_fallback(current_endpoint.name)
                if fallback is None:
                    break
                current_endpoint = fallback
        return OrchestrationResult(
            request_id=request.request_id,
            provider=current_endpoint.provider if current_endpoint else "unknown",
            model=current_endpoint.model_id if current_endpoint else "unknown",
            latency_ms=0.0,
            tokens_used=0,
            success=False,
            error=last_error or "No candidate model available",
        )

    def dispatch(self, request: OrchestrationRequest, runner) -> OrchestrationResult:
        result = self._execute_with_fallback(request, runner)
        with self.lock:
            self.history.append(result)
        return result

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            total = len(self.history)
            successes = sum(1 for h in self.history if h.success)
            fallbacks = sum(1 for h in self.history if h.fallback_used)
            return {
                "total_requests": total,
                "success_rate": (successes / max(total, 1)) * 100.0,
                "fallback_rate": (fallbacks / max(total, 1)) * 100.0,
                "recent_errors": [h.error for h in self.history[-20:] if not h.success],
                "router": self.router.get_stats(),
            }
