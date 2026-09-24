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
