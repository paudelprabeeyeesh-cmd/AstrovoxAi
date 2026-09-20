import pytest
from app.rate_limiter import rate_limiter, RateLimiter


def test_rate_limiter_initial_state():
    limiter = RateLimiter()
    limiter.enabled = False
    assert limiter.check("test-key") is True


def test_rate_limiter_allows_under_limit():
    limiter = RateLimiter()
    limiter.enabled = True
    limiter.default_max = 5
    for _ in range(5):
        assert limiter.check("test-key") is True


def test_rate_limiter_blocks_over_limit():
    limiter = RateLimiter()
    limiter.enabled = True
    limiter.default_max = 2
    assert limiter.check("test-key") is True
    assert limiter.check("test-key") is True
    assert limiter.check("test-key") is False
