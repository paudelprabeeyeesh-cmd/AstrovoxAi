"""Simple wrapper around the deep health checker for readiness and liveness."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .health_checks import DeepHealthChecker, HealthCheck


class HealthChecker:
    def __init__(self) -> None:
        self._checkers: DeepHealthChecker = DeepHealthChecker()
        self._is_ready: bool = False

    def register(self, name: str, checker: Any) -> None:
        self._checkers.register(name, checker)

    def check(self, name: str) -> Optional[HealthCheck]:
        return self._checkers.check(name)

    def run_all(self) -> Dict[str, Any]:
        return self._checkers.run_all()

    def set_ready(self, ready: bool = True) -> None:
        self._is_ready = ready

    def is_ready(self) -> bool:
        return self._is_ready and self._checkers.is_healthy()

    def is_alive(self) -> bool:
        return self._checkers.is_healthy()
