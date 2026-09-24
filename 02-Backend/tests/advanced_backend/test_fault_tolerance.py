import time
import time
import threading
import pytest
from advanced_backend.fault_tolerance import (
    Bulkhead,
    CircuitBreaker,
    TimeoutPolicy,
)


def boom():
    raise RuntimeError("fail")


def ok():
    return "ok"


def test_circuit_closed_to_open():
    cb = CircuitBreaker(name="svc", failure_threshold=2)
    with pytest.raises(RuntimeError):
        cb.call(boom)
    with pytest.raises(RuntimeError):
        cb.call(boom)
    assert cb.state() == "open"


def test_circuit_open_rejects():
    cb = CircuitBreaker(name="svc", failure_threshold=1, recovery_timeout=10)
    with pytest.raises(RuntimeError):
        cb.call(boom)
    with pytest.raises(RuntimeError):
        cb.call(ok)
    assert cb.state() == "open"


def test_circuit_half_open_recovery():
    cb = CircuitBreaker(name="svc", failure_threshold=1, recovery_timeout=0.05)
    with pytest.raises(RuntimeError):
        cb.call(boom)
    time.sleep(0.06)
    result = cb.call(ok)
    assert result == "ok"
    assert cb.state() == "closed"


def test_bulkhead_limits():
    bh = Bulkhead(max_concurrent=1)
    gate = threading.Event()
    def block():
        gate.wait()
    t = threading.Thread(target=bh.execute, args=(block,))
    t.start()
    time.sleep(0.1)
    with pytest.raises(RuntimeError):
        bh.execute(ok)
    gate.set()
    t.join()


def test_bulkhead_releases():
    bh = Bulkhead(max_concurrent=1)
    gate = threading.Event()
    def block():
        gate.wait()
    t = threading.Thread(target=bh.execute, args=(block,))
    t.start()
    time.sleep(0.1)
    assert bh.active() == 1
    gate.set()
    t.join(timeout=5)
    time.sleep(0.05)
    assert bh.active() == 0


def test_circuit_metrics():
    cb = CircuitBreaker(name="m")
    with pytest.raises(RuntimeError):
        cb.call(boom)
    m = cb.metrics()
    assert m["name"] == "m"
    assert m["failures"] == 1
