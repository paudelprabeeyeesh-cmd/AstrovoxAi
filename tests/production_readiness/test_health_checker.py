"""Tests for production_readiness health_checker."""
from __future__ import annotations

from typing import Any, Dict, Optional

from production_readiness.health_checker import HealthChecker
from production_readiness.health_checks import HealthCheck


class StubChecker:
    def __init__(self, result: Dict[str, Any]) -> None:
        self._result = result

    def run_all(self) -> Dict[str, Any]:
        return self._result


def test_register_and_check() -> None:
    checker = HealthChecker()
    checker.register("db", lambda: HealthCheck(name="db", status="healthy"))
    result = checker.check("db")
    assert result is not None
    assert result.status == "healthy"


def test_check_missing_returns_none() -> None:
    checker = HealthChecker()
    assert checker.check("missing") is None


def test_is_ready_before_set() -> None:
    checker = HealthChecker()
    assert checker.is_ready() is False


def test_is_ready_after_set_healthy() -> None:
    checker = HealthChecker()
    checker.register("db", lambda: HealthCheck(name="db", status="healthy"))
    checker.set_ready(True)
    assert checker.is_ready() is True


def test_is_alive_false_when_unhealthy() -> None:
    checker = HealthChecker()
    checker.register("db", lambda: HealthCheck(name="db", status="unhealthy"))
    assert checker.is_alive() is False
