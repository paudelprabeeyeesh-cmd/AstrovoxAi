"""Tests for production_readiness dependency_health."""
from __future__ import annotations

from production_readiness.dependency_health import DependencyHealth


class HealthyStub:
    def run_all(self) -> Dict[str, Any]:
        return {"status": "healthy"}


class FailingStub:
    def run_all(self) -> Dict[str, Any]:
        raise RuntimeError("boom")


def test_register_and_check_healthy() -> None:
    dh = DependencyHealth()
    dh.register("db", HealthyStub())
    result = dh.check("db")
    assert result["status"] == "healthy"


def test_register_and_check_failing() -> None:
    dh = DependencyHealth()
    dh.register("db", FailingStub())
    result = dh.check("db")
    assert result["status"] == "unhealthy"


def test_is_healthy_when_all_pass() -> None:
    dh = DependencyHealth()
    dh.register("db", HealthyStub())
    dh.register("cache", HealthyStub())
    assert dh.is_healthy() is True


def test_is_healthy_when_one_fails() -> None:
    dh = DependencyHealth()
    dh.register("db", HealthyStub())
    dh.register("cache", FailingStub())
    assert dh.is_healthy() is False
