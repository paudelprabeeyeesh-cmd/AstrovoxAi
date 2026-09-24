import pytest
from app.fault_tolerance.health_checker import HealthChecker, HealthStatus


def test_health_checker_register_and_check():
    checker = HealthChecker()
    checker.register("db", lambda: {"latency_ms": 1})
    status = checker.check("db")
    assert status.healthy is True
    assert status.details["latency_ms"] == 1


def test_health_checker_failure():
    checker = HealthChecker()
    checker.register("db", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    status = checker.check("db")
    assert status.healthy is False
    assert "down" in status.message


def test_health_checker_unknown():
    checker = HealthChecker()
    with pytest.raises(ValueError):
        checker.check("unknown")


def test_run_all():
    checker = HealthChecker()
    checker.register("a", lambda: True)
    checker.register("b", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    results = checker.run_all()
    assert results["a"].healthy is True
    assert results["b"].healthy is False


def test_is_healthy():
    checker = HealthChecker()
    checker.register("a", lambda: True)
    checker.register("b", lambda: True)
    assert checker.is_healthy() is True
    checker.register("c", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    assert checker.is_healthy() is False
