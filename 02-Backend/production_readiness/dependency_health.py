"""Dependency health aggregation."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .health_checks import HealthCheck

logger = logging.getLogger(__name__)


class DependencyHealth:
    def __init__(self) -> None:
        self._dependencies: Dict[str, Any] = {}
        self._statuses: Dict[str, str] = {}
        self._last_checked: Dict[str, float] = {}

    def register(self, name: str, health_check: Any) -> None:
        self._dependencies[name] = health_check

    def check(self, name: str) -> Dict[str, Any]:
        checker = self._dependencies.get(name)
        if checker is None:
            return {"name": name, "status": "unknown"}
        try:
            if hasattr(checker, "run_all"):
                payload = checker.run_all()
                status = payload.get("status", "unknown")
            else:
                status = "healthy"
        except Exception as exc:  # noqa: BLE001
            status = "unhealthy"
        return {"name": name, "status": status}

    def check_all(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for name in self._dependencies.keys():
            results.append(self.check(name))
        return results

    def is_healthy(self) -> bool:
        return all(item.get("status") == "healthy" for item in self.check_all())
