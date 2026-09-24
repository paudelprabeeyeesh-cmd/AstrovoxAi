"""Adaptive rate limiting and token bucket."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TokenBucketState:
    tokens: float
    last_refill: float


class TokenBucket:
    def __init__(self, refill_rate: float, burst_capacity: int, enabled: bool = True) -> None:
        self._refill_rate = refill_rate
        self._burst_capacity = burst_capacity
        self._enabled = enabled
        self._buckets: Dict[str, TokenBucketState] = {}
        self._lock = threading.Lock()

    def _refill(self, state: TokenBucketState) -> None:
        now = time.time()
        elapsed = now - state.last_refill
        state.tokens = min(self._burst_capacity, state.tokens + elapsed * self._refill_rate)
        state.last_refill = now

    def check(self, key: str, cost: float = 1.0) -> bool:
        if not self._enabled:
            return True
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucketState(tokens=float(self._burst_capacity), last_refill=time.time())
            state = self._buckets[key]
            self._refill(state)
            if state.tokens >= cost:
                state.tokens -= cost
                return True
            return False

    def remaining(self, key: str) -> float:
        with self._lock:
            if key not in self._buckets:
                return float(self._burst_capacity)
            state = self._buckets[key]
            self._refill(state)
            return state.tokens

    def reset(self, key: str) -> None:
        with self._lock:
            if key in self._buckets:
                state = self._buckets[key]
                state.tokens = float(self._burst_capacity)
                state.last_refill = time.time()


class AdaptiveRateLimiter:
    def __init__(self, base_refill_rate: float, max_refill_rate: float, burst_capacity: int) -> None:
        self._base_refill_rate = base_refill_rate
        self._max_refill_rate = max_refill_rate
        self._current_refill_rate = base_refill_rate
        self._burst_capacity = burst_capacity
        self._buckets: Dict[str, TokenBucketState] = {}
        self._lock = threading.Lock()
        self._load_history: List[float] = []
        self._history_lock = threading.Lock()

    def _get_load(self) -> float:
        with self._history_lock:
            if not self._load_history:
                return 0.5
            return sum(self._load_history[-10:]) / min(len(self._load_history[-10:]), 10)

    def _adjust_rate(self) -> None:
        load = self._get_load()
        factor = 1.0 - load
        self._current_refill_rate = max(self._base_refill_rate, min(self._max_refill_rate, self._base_refill_rate * factor + self._max_refill_rate * load))

    def record_load(self, load: float) -> None:
        with self._history_lock:
            self._load_history.append(max(0.0, min(1.0, load)))

    def check(self, key: str, cost: float = 1.0) -> bool:
        self._adjust_rate()
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = TokenBucketState(tokens=float(self._burst_capacity), last_refill=time.time())
            state = self._buckets[key]
            now = time.time()
            elapsed = now - state.last_refill
            state.tokens = min(self._burst_capacity, state.tokens + elapsed * self._current_refill_rate)
            state.last_refill = now
            if state.tokens >= cost:
                state.tokens -= cost
                return True
            return False

    def remaining(self, key: str) -> float:
        with self._lock:
            if key not in self._buckets:
                return float(self._burst_capacity)
            state = self._buckets[key]
            now = time.time()
            elapsed = now - state.last_refill
            state.tokens = min(self._burst_capacity, state.tokens + elapsed * self._current_refill_rate)
            state.last_refill = now
            return state.tokens


class RateLimitingStrategy:
    FIXED = "fixed"
    ADAPTIVE = "adaptive"


class RateLimitingAdvanced:
    def __init__(self) -> None:
        self._limiters: Dict[str, Tuple[RateLimitingStrategy, TokenBucket | AdaptiveRateLimiter]] = {}
        self._lock = threading.Lock()

    def register(self, name: str, strategy: RateLimitingStrategy, refill_rate: float, burst_capacity: int, max_refill_rate: Optional[float] = None) -> None:
        with self._lock:
            if strategy == RateLimitingStrategy.ADAPTIVE:
                self._limiters[name] = (strategy, AdaptiveRateLimiter(refill_rate, max_refill_rate or refill_rate, burst_capacity))
            else:
                self._limiters[name] = (strategy, TokenBucket(refill_rate, burst_capacity))

    def check(self, name: str, key: str, cost: float = 1.0) -> bool:
        with self._lock:
            entry = self._limiters.get(name)
            if entry is None:
                return False
            _, limiter = entry
            return limiter.check(key, cost)

    def get_limiter(self, name: str) -> Optional[TokenBucket | AdaptiveRateLimiter]:
        with self._lock:
            entry = self._limiters.get(name)
            if entry is None:
                return None
            return entry[1]
