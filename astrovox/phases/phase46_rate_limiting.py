"""Token-bucket rate limiter."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """A single token bucket."""
    capacity: float
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=time.time)
    key: str = "default"

    def consume(self, n: int = 1) -> bool:
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class RateLimiter:
    """Global rate limiter with per-key buckets."""

    def __init__(self, capacity: float = 100.0, refill_rate: float = 10.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: dict[str, TokenBucket] = {}

    def _bucket(self, key: str) -> TokenBucket:
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(capacity=self.capacity, tokens=self.capacity,
                                            refill_rate=self.refill_rate, key=key)
        return self.buckets[key]

    def allow(self, key: str = "default", n: int = 1) -> bool:
        """Check if a request is allowed."""
        return self._bucket(key).consume(n)

    def remaining(self, key: str = "default") -> float:
        """Return remaining tokens for a key."""
        return self._bucket(key).tokens

    def reset(self, key: str = "default") -> None:
        b = self._bucket(key)
        b.tokens = b.capacity
        b.last_refill = time.time()

    def clear(self) -> None:
        self.buckets.clear()


class TieredRateLimiter:
    """Rate limiting by tier (free/pro/premium)."""

    TIERS = {"free": (10.0, 1.0), "pro": (100.0, 10.0), "premium": (1000.0, 100.0)}

    def __init__(self):
        self.limiters: dict[str, RateLimiter] = {}

    def tier_for(self, key: str) -> str:
        return "free"

    def allow(self, key: str, n: int = 1) -> bool:
        tier = self.tier_for(key)
        cap, rate = self.TIERS.get(tier, self.TIERS["free"])
        limiter = self.limiters.setdefault(key, RateLimiter(capacity=cap, refill_rate=rate))
        return limiter.allow(key, n)

    def reset(self, key: str) -> None:
        limiter = self.limiters.get(key)
        if limiter:
            limiter.reset(key)

    def clear(self) -> None:
        self.limiters.clear()
