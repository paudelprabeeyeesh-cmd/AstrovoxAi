import time
import pytest
from production_readiness.rate_limiting_advanced import TokenBucket, AdaptiveRateLimiter, RateLimitingStrategy, RateLimitingAdvanced


def test_token_bucket_allows():
    bucket = TokenBucket(refill_rate=1.0, burst_capacity=10)
    assert bucket.check("user-1") is True
    assert pytest.approx(bucket.remaining("user-1"), abs=0.1) == 9.0


def test_token_bucket_blocks():
    bucket = TokenBucket(refill_rate=1.0, burst_capacity=10)
    for _ in range(10):
        assert bucket.check("user-1") is True
    assert bucket.check("user-1") is False


def test_token_bucket_refill():
    bucket = TokenBucket(refill_rate=100.0, burst_capacity=10)
    for _ in range(10):
        assert bucket.check("user-1") is True
    assert bucket.check("user-1") is False
    time.sleep(0.1)
    assert bucket.check("user-1") is True


def test_token_bucket_reset():
    bucket = TokenBucket(refill_rate=1.0, burst_capacity=10)
    for _ in range(10):
        assert bucket.check("user-1") is True
    assert bucket.check("user-1") is False
    bucket.reset("user-1")
    assert bucket.check("user-1") is True


def test_adaptive_rate_limiter():
    limiter = AdaptiveRateLimiter(base_refill_rate=1.0, max_refill_rate=5.0, burst_capacity=10)
    assert limiter.check("user-1") is True
    limiter.record_load(0.9)
    limiter.check("user-1", 5.0)
    assert limiter.remaining("user-1") == 0.0


def test_adaptive_rate_limiter_adjusts():
    limiter = AdaptiveRateLimiter(base_refill_rate=1.0, max_refill_rate=5.0, burst_capacity=10)
    for _ in range(10):
        assert limiter.check("user-1") is True
    assert limiter.check("user-1") is False
    limiter.record_load(0.1)
    time.sleep(0.1)
    assert limiter.check("user-1") is True


def test_rate_limiting_advanced():
    rl = RateLimitingAdvanced()
    rl.register("default", RateLimitingStrategy.FIXED, 1.0, 10)
    assert rl.check("default", "user-1") is True


def test_rate_limiting_adaptive_strategy():
    rl = RateLimitingAdvanced()
    rl.register("default", RateLimitingStrategy.ADAPTIVE, 1.0, 10, max_refill_rate=5.0)
    assert rl.check("default", "user-1") is True
