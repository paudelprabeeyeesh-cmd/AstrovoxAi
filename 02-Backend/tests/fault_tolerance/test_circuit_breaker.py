import time

import pytest
from app.fault_tolerance.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_breaker_initial_state():
    cb = CircuitBreaker()
    assert cb.get_state() == "closed"
    assert cb.failure_count == 0


def test_circuit_breaker_success():
    cb = CircuitBreaker()
    result = cb.call(lambda: "ok")
    assert result == "ok"
    assert cb.get_state() == "closed"


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    for _ in range(3):
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    assert cb.get_state() == "open"


def test_circuit_breaker_blocks_when_open():
    cb = CircuitBreaker(failure_threshold=2)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    with pytest.raises(RuntimeError, match="Circuit breaker is open"):
        cb.call(lambda: "should not run")


def test_circuit_breaker_reset():
    cb = CircuitBreaker(failure_threshold=2)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    cb.reset()
    assert cb.get_state() == "closed"
    assert cb.call(lambda: "ok") == "ok"


def test_circuit_breaker_recovery_to_half_open():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    time.sleep(0.15)
    assert cb.get_state() == "half_open"


def test_circuit_breaker_closes_after_success_in_half_open():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, success_threshold=2)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    time.sleep(0.15)
    cb.call(lambda: "ok")
    assert cb.get_state() == "half_open"
    cb.call(lambda: "ok")
    assert cb.get_state() == "closed"


def test_circuit_breaker_call_passes_args():
    cb = CircuitBreaker()
    result = cb.call(lambda x, y: x + y, 2, y=3)
    assert result == 5


def test_circuit_breaker_failure_count_resets_on_success():
    cb = CircuitBreaker(failure_threshold=5)
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    assert cb.failure_count == 1
    cb.call(lambda: "ok")
    assert cb.failure_count == 0


def test_circuit_breaker_success_count_increments_in_half_open():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, success_threshold=2)
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    time.sleep(0.15)
    cb.call(lambda: "ok")
    assert cb.success_count == 1
    cb.call(lambda: "ok")
    assert cb.get_state() == "closed"


def test_circuit_breaker_opened_at_set():
    cb = CircuitBreaker(failure_threshold=1)
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    assert cb.opened_at is not None
    assert cb.get_state() == "open"


def test_circuit_breaker_last_failure_time_set():
    cb = CircuitBreaker(failure_threshold=1)
    before = time.time()
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    assert cb.last_failure_time is not None
    assert cb.last_failure_time >= before


def test_circuit_breaker_should_attempt_reset_false_when_no_opened_at():
    cb = CircuitBreaker()
    assert cb._should_attempt_reset() is False


def test_circuit_breaker_reset_clears_timestamps():
    cb = CircuitBreaker(failure_threshold=1)
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    cb.reset()
    assert cb.opened_at is None
    assert cb.last_failure_time is None


def test_circuit_breaker_half_open_blocks_until_recovery():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.2)
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    with pytest.raises(RuntimeError, match="Circuit breaker is open"):
        cb.call(lambda: "should not run")
    time.sleep(0.25)
    assert cb.get_state() == "half_open"
    result = cb.call(lambda: "recovered")
    assert result == "recovered"
    assert cb.get_state() == "closed"
