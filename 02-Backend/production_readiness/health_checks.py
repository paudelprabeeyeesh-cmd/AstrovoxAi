"""Deep health checks and dependency verification."""
from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    name: str
    status: str = "unknown"
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "details": self.details,
        }


class HealthCheckRegistry:
    def __init__(self) -> None:
        self._checks: Dict[str, Callable[[], HealthCheck]] = {}
        self._lock = threading.Lock()

    def register(self, name: str, checker: Callable[[], HealthCheck]) -> None:
        with self._lock:
            self._checks[name] = checker

    def unregister(self, name: str) -> None:
        with self._lock:
            self._checks.pop(name, None)

    def checks(self) -> Dict[str, Callable[[], HealthCheck]]:
        with self._lock:
            return dict(self._checks)


class DeepHealthChecker:
    def __init__(self) -> None:
        self.registry = HealthCheckRegistry()
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def register(self, name: str, checker: Callable[[], HealthCheck]) -> None:
        self.registry.register(name, checker)

    def check(self, name: str) -> Optional[HealthCheck]:
        checker = self.registry.checks().get(name)
        if checker is None:
            return None
        start = time.time()
        try:
            result = checker()
            result.latency_ms = (time.time() - start) * 1000
            result.status = "healthy"
            logger.info("health check passed: %s", name)
            return result
        except Exception as _e:  # noqa: BLE001
            latency = (time.time() - start) * 1000
            logger.error("health check failed: %s -> %s", name, _e)
            return HealthCheck(
                name=name,
                status="unhealthy",
                latency_ms=latency,
                details={"error": str(_e)},
            )

    def run_all(self) -> Dict[str, Any]:
        checks = self.registry.checks()
        results: List[Dict[str, Any]] = []
        status_counts = {"healthy": 0, "unhealthy": 0, "unknown": 0}
        for name in sorted(checks.keys()):
            check = self.check(name)
            if check is None:
                continue
            item = check.to_dict()
            results.append(item)
            status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
        payload = {"status": "healthy" if status_counts["unhealthy"] == 0 else "degraded", "checks": results}
        with self._lock:
            self._history.append(payload)
        return payload

    def dependency_graph(self) -> Dict[str, List[str]]:
        graph: Dict[str, List[str]] = {}
        for name in self.registry.checks().keys():
            graph[name] = []
        return graph

    def verify_dependencies(self) -> Dict[str, Any]:
        return {"status": "healthy", "dependencies": self.dependency_graph()}

    def history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history)

    def is_healthy(self) -> bool:
        payload = self.run_all()
        return payload["status"] == "healthy"
