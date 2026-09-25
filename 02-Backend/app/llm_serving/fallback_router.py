"""Model fallback router with health probes and automatic failover."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class HealthProbeResult:
    model_id: str
    is_healthy: bool
    latency_ms: float
    error: Optional[str] = None
    checked_at: float = field(default_factory=time.time)


@dataclass
class FallbackRoute:
    route_id: str
    primary: str
    fallbacks: list[str]
    max_retries: int = 2
    retry_delay: float = 1.0
    health_check_interval: float = 30.0
    consecutive_failures_before_disable: int = 3


class HealthProbe:
    def __init__(self, check_interval: float = 30.0, timeout: float = 5.0):
        self._check_interval = check_interval
        self._timeout = timeout
        self._last_check: dict[str, float] = {}
        self._results: dict[str, HealthProbeResult] = {}

    def should_check(self, model_id: str) -> bool:
        last = self._last_check.get(model_id, 0.0)
        return time.time() - last >= self._check_interval

    def record(self, result: HealthProbeResult) -> None:
        self._last_check[result.model_id] = result.checked_at
        self._results[result.model_id] = result

    def get(self, model_id: str) -> Optional[HealthProbeResult]:
        return self._results.get(model_id)


class ModelFallbackRouter:
    def __init__(
        self,
        health_probe: Optional[HealthProbe] = None,
        default_route: Optional[FallbackRoute] = None,
    ):
        self._health_probe = health_probe or HealthProbe()
        self._routes: dict[str, FallbackRoute] = {}
        self._adapters: dict[str, Any] = {}
        self._default_route = default_route or FallbackRoute(
            route_id="default",
            primary="gpt-4o-mini",
            fallbacks=["gpt-4o", "claude-3-haiku"],
        )
        self._register_route(self._default_route)

    def register_adapter(self, model_id: str, adapter: Any) -> None:
        self._adapters[model_id] = adapter

    def register_route(self, route: FallbackRoute) -> None:
        self._register_route(route)

    def _register_route(self, route: FallbackRoute) -> None:
        self._routes[route.route_id] = route
        for model_id in [route.primary] + route.fallbacks:
            if model_id not in self._adapters:
                self._adapters[model_id] = None

    def get_route(self, route_id: Optional[str] = None) -> list[str]:
        route = self._routes.get(route_id) if route_id else self._default_route
        if not route:
            return [self._default_route.primary] + self._default_route.fallbacks
        candidates = [route.primary] + route.fallbacks
        healthy = [m for m in candidates if self._is_healthy(m)]
        return healthy if healthy else candidates

    def route(self, route_id: Optional[str] = None) -> str:
        candidates = self.get_route(route_id)
        return candidates[0] if candidates else self._default_route.primary

    def execute_with_fallback(
        self,
        route_id: Optional[str],
        request: Any,
        max_retries: Optional[int] = None,
    ) -> Any:
        candidates = self.get_route(route_id)
        max_attempts = max_retries or self._default_route.max_retries
        attempts = 0
        last_error = None
        for model_id in candidates:
            if attempts >= max_attempts:
                break
            adapter = self._adapters.get(model_id)
            if not adapter:
                continue
            try:
                if not self._health_probe.should_check(model_id):
                    result = adapter.generate(request)
                    self._record_success(model_id, getattr(result, "latency_ms", 0.0))
                    return result
                result = adapter.generate(request)
                self._record_success(model_id, getattr(result, "latency_ms", 0.0))
                return result
            except Exception as exc:
                last_error = str(exc)
                self._record_failure(model_id, last_error)
                attempts += 1
                time.sleep(self._default_route.retry_delay)
        raise RuntimeError(f"All fallbacks exhausted: {last_error}")

    def _is_healthy(self, model_id: str) -> bool:
        result = self._health_probe.get(model_id)
        if not result:
            return True
        return result.is_healthy

    def _record_success(self, model_id: str, latency_ms: float) -> None:
        result = HealthProbeResult(
            model_id=model_id,
            is_healthy=True,
            latency_ms=latency_ms,
            checked_at=time.time(),
        )
        self._health_probe.record(result)

    def _record_failure(self, model_id: str, error: str) -> None:
        result = HealthProbeResult(
            model_id=model_id,
            is_healthy=False,
            latency_ms=0.0,
            error=error,
            checked_at=time.time(),
        )
        self._health_probe.record(result)

    def health_report(self) -> dict[str, Any]:
        return {
            model_id: {
                "is_healthy": r.is_healthy if r else None,
                "latency_ms": r.latency_ms if r else None,
                "error": r.error if r else None,
                "checked_at": r.checked_at if r else None,
            }
            for model_id, r in self._health_probe._results.items()
        }
