import time
import pytest
from production_readiness.health_checks import DeepHealthChecker, HealthCheckRegistry, HealthCheck


class SimpleChecker:
    def __init__(self, result):
        self._result = result

    def run(self):
        return self._result


def test_health_check_registration():
    checker = DeepHealthChecker()
    checker.register("db", lambda: HealthCheck(name="db", status="healthy"))
    assert checker.check("db") is not None
    assert checker.check("db").status == "healthy"


def test_health_check_unhealthy():
    checker = DeepHealthChecker()
    checker.register("db", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    assert checker.check("db") is not None
    assert checker.check("db").status == "unhealthy"


def test_run_all():
    checker = DeepHealthChecker()
    checker.register("db", lambda: HealthCheck(name="db", status="healthy"))
    checker.register("cache", lambda: HealthCheck(name="cache", status="healthy"))
    payload = checker.run_all()
    assert payload["status"] == "healthy"
    assert len(payload["checks"]) == 2


def test_run_all_degraded():
    checker = DeepHealthChecker()
    checker.register("db", lambda: HealthCheck(name="db", status="healthy"))
    checker.register("cache", lambda: (_ for _ in ()).throw(RuntimeError("cache down")))
    payload = checker.run_all()
    assert payload["status"] == "degraded"


def test_dependency_graph():
    checker = DeepHealthChecker()
    checker.register("db", lambda: HealthCheck(name="db"))
    checker.register("cache", lambda: HealthCheck(name="cache"))
    graph = checker.dependency_graph()
    assert "db" in graph
    assert "cache" in graph


def test_history():
    checker = DeepHealthChecker()
    checker.register("db", lambda: HealthCheck(name="db", status="healthy"))
    checker.run_all()
    assert len(checker.history()) == 1


def test_is_healthy():
    checker = DeepHealthChecker()
    checker.register("db", lambda: HealthCheck(name="db", status="healthy"))
    checker.register("cache", lambda: HealthCheck(name="cache", status="healthy"))
    assert checker.is_healthy() is True
