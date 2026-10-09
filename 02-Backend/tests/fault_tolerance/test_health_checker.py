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


def test_health_checker_register_overwrites():
    checker = HealthChecker()
    checker.register("db", lambda: False)
    checker.register("db", lambda: True)
    status = checker.check("db")
    assert status.healthy is True


def test_health_checker_empty_details_by_default():
    checker = HealthChecker()
    checker.register("db", lambda: True)
    status = checker.check("db")
    assert status.details == {}


def test_health_checker_details_populated():
    checker = HealthChecker()
    checker.register("db", lambda: {"latency_ms": 42, "status": "ok"})
    status = checker.check("db")
    assert status.details["latency_ms"] == 42
    assert status.details["status"] == "ok"


def test_health_checker_message_on_failure():
    checker = HealthChecker()
    checker.register("db", lambda: (_ for _ in ()).throw(RuntimeError("connection refused")))
    status = checker.check("db")
    assert status.healthy is False
    assert "connection refused" in status.message


def test_health_checker_check_with_args():
    checker = HealthChecker()
    checker.register("db", lambda timeout: {"timeout": timeout})
    status = checker.check("db", 5)
    assert status.details["timeout"] == 5


def test_health_status_repr():
    status = HealthStatus(name="db", healthy=True)
    assert repr(status) == "HealthStatus(name='db', healthy=True)"


def test_run_all_returns_all_registered():
    checker = HealthChecker()
    checker.register("a", lambda: True)
    checker.register("b", lambda: True)
    checker.register("c", lambda: True)
    results = checker.run_all()
    assert set(results.keys()) == {"a", "b", "c"}
    assert all(r.healthy for r in results.values())


def test_is_healthy_with_no_checks():
    checker = HealthChecker()
    assert checker.is_healthy() is True
