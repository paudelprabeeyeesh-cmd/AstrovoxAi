import time
import pytest
from production_readiness.graceful_degradation import GracefulDegradation, FallbackMode, CircuitBreaker


class FaultyService:
    def __init__(self):
        self.fails = False
        self.calls = 0

    def call(self):
        self.calls += 1
        if self.fails:
            raise RuntimeError("service down")
        return "ok"


def test_circuit_breaker_closed():
    cb = CircuitBreaker(name="svc", failure_threshold=3)
    assert cb.allow_request() is True
    cb.record_success()
    assert cb.state == "closed"


def test_circuit_breaker_opens():
    cb = CircuitBreaker(name="svc", failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    assert cb.allow_request() is False
    assert cb.state == "open"


def test_circuit_breaker_half_open():
    cb = CircuitBreaker(name="svc", failure_threshold=3, recovery_timeout=0.1)
    for _ in range(3):
        cb.record_failure()
    assert cb.allow_request() is False
    time.sleep(0.2)
    assert cb.allow_request() is True
    assert cb.state == "half_open"


def test_graceful_degradation_success():
    gd = GracefulDegradation()
    svc = FaultyService()
    result = gd.execute_with_degradation("svc", svc.call)
    assert result == "ok"


def test_graceful_degradation_circuit_breaker():
    gd = GracefulDegradation()
    gd.register_fallback(FallbackMode.DEFAULT, lambda: "fallback")
    svc = FaultyService()
    for _ in range(5):
        svc.fails = True
        with pytest.raises(RuntimeError):
            gd.execute_with_degradation("svc", svc.call, FallbackMode.DEFAULT)
    svc.fails = False
    result = gd.execute_with_degradation("svc", svc.call, FallbackMode.DEFAULT)
    assert result == "fallback"


def test_graceful_degradation_status():
    gd = GracefulDegradation()
    gd.register_circuit_breaker("svc")
    status = gd.status()
    assert "svc" in status
