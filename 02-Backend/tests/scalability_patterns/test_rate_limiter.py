import time

from scalability_patterns.rate_limiter import RateLimiter


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


def test_rate_limiter_reset():
    limiter = RateLimiter()
    limiter.enabled = True
    limiter.default_max = 1
    assert limiter.check("k") is True
    assert limiter.check("k") is False
    limiter.reset("k")
    assert limiter.check("k") is True


def test_rate_limiter_remaining():
    limiter = RateLimiter()
    limiter.enabled = True
    limiter.default_max = 3
    limiter.check("k")
    limiter.check("k")
    assert limiter.remaining("k") == 1
