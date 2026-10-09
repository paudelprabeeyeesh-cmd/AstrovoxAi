import time

import pytest
from app.fault_tolerance.retry_policy import RetryPolicy, BackoffStrategy


def test_retry_succeeds_on_first_attempt():
    policy = RetryPolicy(max_retries=2)
    result = policy.execute(lambda: "ok")
    assert result == "ok"


def test_retry_raises_after_max_retries():
    policy = RetryPolicy(max_retries=2)
    with pytest.raises(RuntimeError):
        policy.execute(lambda: (_ for _ in ()).throw(RuntimeError("fail")))


def test_retry_succeeds_after_failures():
    policy = RetryPolicy(max_retries=3)
    calls = {"count": 0}

    def func():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("fail")
        return "ok"

    result = policy.execute(func)
    assert result == "ok"
    assert calls["count"] == 3


def test_retry_non_retryable_exception():
    policy = RetryPolicy(max_retries=3, retryable_exceptions=(ValueError,))
    with pytest.raises(RuntimeError):
        policy.execute(lambda: (_ for _ in ()).throw(RuntimeError("fail")))


def test_should_retry_true():
    policy = RetryPolicy(max_retries=3)
    assert policy.should_retry(1, RuntimeError("fail")) is True


def test_should_retry_false_at_max():
    policy = RetryPolicy(max_retries=3)
    assert policy.should_retry(3, RuntimeError("fail")) is False


def test_retry_fixed_backoff():
    policy = RetryPolicy(max_retries=2, backoff_strategy=BackoffStrategy.FIXED, base_delay=0.05)
    times = []
    start = time.time()

    def func():
        times.append(time.time() - start)
        if len(times) < 3:
            raise RuntimeError("fail")
        return "ok"

    result = policy.execute(func)
    assert result == "ok"
    assert len(times) == 3
    assert times[1] - times[0] >= 0.05
    assert times[2] - times[1] >= 0.05


def test_retry_exponential_backoff():
    policy = RetryPolicy(max_retries=3, backoff_strategy=BackoffStrategy.EXPONENTIAL, base_delay=0.05)
    times = []
    start = time.time()

    def func():
        times.append(time.time() - start)
        if len(times) < 4:
            raise RuntimeError("fail")
        return "ok"

    result = policy.execute(func)
    assert result == "ok"
    assert len(times) == 4
    assert times[1] - times[0] >= 0.05
    assert times[2] - times[1] >= 0.10
    assert times[3] - times[2] >= 0.20


def test_retry_exponential_backoff_respects_max_delay():
    policy = RetryPolicy(max_retries=4, backoff_strategy=BackoffStrategy.EXPONENTIAL, base_delay=1.0, max_delay=0.3)
    times = []
    start = time.time()

    def func():
        times.append(time.time() - start)
        if len(times) < 5:
            raise RuntimeError("fail")
        return "ok"

    result = policy.execute(func)
    assert result == "ok"
    assert len(times) == 5
    assert times[4] - times[3] >= 0.3


def test_retry_execute_passes_args():
    policy = RetryPolicy(max_retries=1)
    result = policy.execute(lambda x, y: x + y, 2, y=3)
    assert result == 5


def test_retry_non_retryable_exception_is_raised_immediately():
    policy = RetryPolicy(max_retries=3, retryable_exceptions=(ValueError,))
    with pytest.raises(RuntimeError):
        policy.execute(lambda: (_ for _ in ()).throw(RuntimeError("fail")))


def test_retry_zero_max_retries():
    policy = RetryPolicy(max_retries=0)
    with pytest.raises(RuntimeError):
        policy.execute(lambda: (_ for _ in ()).throw(RuntimeError("fail")))


def test_should_retry_with_non_retryable_exception():
    policy = RetryPolicy(max_retries=3, retryable_exceptions=(ValueError,))
    assert policy.should_retry(1, RuntimeError("fail")) is False


def test_retry_no_sleep_on_last_attempt():
    policy = RetryPolicy(max_retries=1, backoff_strategy=BackoffStrategy.FIXED, base_delay=0.001)
    start = time.time()
    with pytest.raises(RuntimeError):
        policy.execute(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    elapsed = time.time() - start
    assert elapsed < 0.1


def test_retry_custom_retryable_exceptions():
    policy = RetryPolicy(max_retries=2, retryable_exceptions=(ValueError, TypeError))

    def func():
        if "called" not in func.__dict__:
            func.called = True
            raise ValueError("retryable")
        return "ok"

    result = policy.execute(func)
    assert result == "ok"
