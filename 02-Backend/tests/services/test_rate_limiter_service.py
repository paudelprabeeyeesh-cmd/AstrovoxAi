import time
from services.rate_limiter_service import RateLimiterService


class TestRateLimiterService:
    def test_allows_under_limit(self):
        svc = RateLimiterService()
        assert svc.is_allowed("key", limit=2, window=60) is True
        assert svc.is_allowed("key", limit=2, window=60) is True
        assert svc.is_allowed("key", limit=2, window=60) is False

    def test_different_keys_independent(self):
        svc = RateLimiterService()
        assert svc.is_allowed("key-a", limit=1, window=60) is True
        assert svc.is_allowed("key-b", limit=1, window=60) is True
        assert svc.is_allowed("key-a", limit=1, window=60) is False
        assert svc.is_allowed("key-b", limit=1, window=60) is False

    def test_reset_clears_key(self):
        svc = RateLimiterService()
        assert svc.is_allowed("key", limit=1, window=60) is True
        assert svc.is_allowed("key", limit=1, window=60) is False
        svc.reset("key")
        assert svc.is_allowed("key", limit=1, window=60) is True

    def test_window_expiry(self):
        svc = RateLimiterService()
        assert svc.is_allowed("key", limit=1, window=1) is True
        assert svc.is_allowed("key", limit=1, window=1) is False
        time.sleep(1.1)
        assert svc.is_allowed("key", limit=1, window=1) is True
