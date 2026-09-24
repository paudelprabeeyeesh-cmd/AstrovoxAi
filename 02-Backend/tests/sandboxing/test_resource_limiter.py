import sys
import pytest
from sandboxing.resource_limiter import ResourceLimiter


def test_init_defaults():
    limiter = ResourceLimiter()
    assert limiter.max_memory_mb == 256
    assert limiter.max_execution_time == 1.0


def test_init_custom():
    limiter = ResourceLimiter(max_memory_mb=512, max_execution_time=2.0)
    assert limiter.max_memory_mb == 512
    assert limiter.max_execution_time == 2.0


def test_limit_memory_called():
    limiter = ResourceLimiter(max_memory_mb=128)
    limiter.limit_memory()


def test_limit_cpu_time_called():
    limiter = ResourceLimiter()
    limiter.limit_cpu_time()


def test_enforce_called():
    limiter = ResourceLimiter()
    limiter.enforce()


def test_enforce_with_timeout_called():
    limiter = ResourceLimiter(max_execution_time=1.0)
    if sys.platform != "win32":
        limiter.enforce_with_timeout()
    else:
        limiter.enforce_with_timeout()
        assert limiter._timer is not None
        limiter._cancel_timer()
        assert limiter._timer is None


def test_timeout_handler_raises():
    limiter = ResourceLimiter(max_execution_time=0.5)
    with pytest.raises(TimeoutError):
        limiter._timeout_handler()


def test_cancel_timer_noop_when_none():
    limiter = ResourceLimiter()
    limiter._cancel_timer()
