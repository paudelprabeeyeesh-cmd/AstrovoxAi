import time
import threading
from typing import Dict, Optional, Union
from .rate_limiting_token_bucket import TokenBucketRateLimiter
from .sliding_window_rate_limiting import SlidingWindowRateLimiter


class RateLimiter:
    def __init__(
        self,
        strategy: str = "token_bucket",
        window_seconds: float = 60.0,
        max_requests: int = 100,
        refill_rate: float = 1.0,
        burst_capacity: int = 10,
        enabled: bool = True,
    ):
        self._strategy = strategy
        self._enabled = enabled
        if strategy == "sliding_window":
            self._limiter: Union[TokenBucketRateLimiter, SlidingWindowRateLimiter] = (
                SlidingWindowRateLimiter(window_seconds=window_seconds, max_requests=max_requests)
            )
        else:
            self._limiter = TokenBucketRateLimiter(
                refill_rate=refill_rate,
                burst_capacity=burst_capacity,
                enabled=True,
            )
        self._per_key_limiters: Dict[str, Union[TokenBucketRateLimiter, SlidingWindowRateLimiter]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, cost: float = 1.0) -> bool:
        if not self._enabled:
            return True
        with self._lock:
            if key not in self._per_key_limiters:
                if self._strategy == "sliding_window":
                    self._per_key_limiters[key] = SlidingWindowRateLimiter(
                        window_seconds=60.0,
                        max_requests=100,
                    )
                else:
                    self._per_key_limiters[key] = TokenBucketRateLimiter(
                        refill_rate=1.0,
                        burst_capacity=10,
                        enabled=True,
                    )
            limiter = self._per_key_limiters[key]
        if self._strategy == "sliding_window":
            return limiter.check(key)
        return limiter.check(key, cost=cost)

    def reset(self, key: str):
        with self._lock:
            if key in self._per_key_limiters:
                del self._per_key_limiters[key]

    @property
    def strategy(self) -> str:
        return self._strategy

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
