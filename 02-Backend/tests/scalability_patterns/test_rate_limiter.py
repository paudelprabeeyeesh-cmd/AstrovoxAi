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


def test_rate_limiter_per_key_max():
    limiter = RateLimiter()
    limiter.enabled = True
    limiter.default_max = 10
    assert limiter.check("k", max_requests=2) is True
    assert limiter.check("k", max_requests=2) is True
    assert limiter.check("k", max_requests=2) is False


def test_rate_limiter_remaining_when_disabled():
    limiter = RateLimiter(default_max=5)
    limiter.enabled = False
    assert limiter.remaining("k") == 5


def test_rate_limiter_remaining_no_requests():
    limiter = RateLimiter(default_max=7)
    limiter.enabled = True
    assert limiter.remaining("k") == 7


def test_rate_limiter_window_expiry():
    limiter = RateLimiter(default_max=1, window=1)
    limiter.enabled = True
    assert limiter.check("k") is True
    assert limiter.check("k") is False
    time.sleep(1.1)
    assert limiter.check("k") is True


def test_rate_limiter_reset_missing_key():
    limiter = RateLimiter()
    limiter.enabled = True
    limiter.reset("missing")
    assert limiter.check("missing") is True


def test_rate_limiter_enabled_property():
    limiter = RateLimiter()
    assert limiter.enabled is True
    limiter.enabled = False
    assert limiter.enabled is False
    assert limiter.check("k") is True


def test_rate_limiter_thread_safety():
    limiter = RateLimiter(default_max=100)
    limiter.enabled = True
    results = []

    def check_many():
        for _ in range(50):
            results.append(limiter.check("shared-key"))

    threads = [threading.Thread(target=check_many) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2)
    assert len(results) == 200
    assert results.count(True) == 100
    assert results.count(False) == 100
