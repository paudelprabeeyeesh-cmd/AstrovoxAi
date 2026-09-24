import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class BucketState:
    tokens: float
    last_refill: float


class TokenBucketRateLimiter:
    def __init__(
        self,
        refill_rate: float = 1.0,
        burst_capacity: int = 10,
        enabled: bool = True,
    ):
        self._refill_rate = refill_rate
        self._burst_capacity = burst_capacity
        self._enabled = enabled
        self._buckets: Dict[str, BucketState] = {}
        self._lock = threading.Lock()

    def _refill(self, state: BucketState):
        now = time.time()
        elapsed = now - state.last_refill
        state.tokens = min(
            self._burst_capacity,
            state.tokens + elapsed * self._refill_rate,
        )
        state.last_refill = now

    def check(self, key: str, cost: float = 1.0) -> bool:
        if not self._enabled:
            return True
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = BucketState(
                    tokens=self._burst_capacity,
                    last_refill=time.time(),
                )
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

    def reset(self, key: str):
        with self._lock:
            if key in self._buckets:
                state = self._buckets[key]
                state.tokens = self._burst_capacity
                state.last_refill = time.time()

    @property
    def refill_rate(self) -> float:
        return self._refill_rate

    @property
    def burst_capacity(self) -> int:
        return self._burst_capacity


class DistributedTokenBucket:
    def __init__(
        self,
        refill_rate: float = 1.0,
        burst_capacity: int = 10,
        node_id: str = "node-1",
        peers: Optional[list] = None,
    ):
        self._local = TokenBucketRateLimiter(refill_rate, burst_capacity)
        self._node_id = node_id
        self._peers = peers or []
        self._shared_state: Dict[str, Dict[str, float]] = {}
        self._lock = threading.Lock()

    def _aggregate(self, key: str) -> float:
        total = self._local.remaining(key)
        for peer in self._peers:
            peer_state = self._shared_state.get(f"{peer}:{key}")
            if peer_state:
                total += peer_state.get("tokens", 0.0)
        return total

    def check(self, key: str, cost: float = 1.0) -> bool:
        with self._lock:
            available = self._aggregate(key)
            if available >= cost:
                self._local.check(key, cost)
                self._shared_state[f"{self._node_id}:{key}"] = {
                    "tokens": self._local.remaining(key),
                    "last_update": time.time(),
                }
                return True
            return False

    def sync_from_peer(self, peer_id: str, key: str, tokens: float, last_update: float):
        with self._lock:
            self._shared_state[f"{peer_id}:{key}"] = {
                "tokens": tokens,
                "last_update": last_update,
            }
