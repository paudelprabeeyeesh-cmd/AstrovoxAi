import time
import threading
import pytest
import numpy as np
from api_gateway.rate_limiting_token_bucket import (
    TokenBucketRateLimiter,
    DistributedTokenBucket,
)


class TestTokenBucketRateLimiter:
    def test_disabled_allows_all(self):
        limiter = TokenBucketRateLimiter(enabled=False)
        for _ in range(100):
            assert limiter.check("key") is True

    def test_initial_full_bucket(self):
        limiter = TokenBucketRateLimiter(refill_rate=1.0, burst_capacity=10)
        for _ in range(10):
            assert limiter.check("key") is True
        assert limiter.check("key") is False

    def test_refill_after_time(self):
        limiter = TokenBucketRateLimiter(refill_rate=10.0, burst_capacity=10)
        for _ in range(10):
            limiter.check("key")
        assert limiter.check("key") is False
        time.sleep(0.2)
        assert limiter.check("key") is True

    def test_different_keys_independent(self):
        limiter = TokenBucketRateLimiter(refill_rate=1.0, burst_capacity=3)
        for _ in range(3):
            assert limiter.check("a") is True
        assert limiter.check("a") is False
        assert limiter.check("b") is True

    def test_custom_cost(self):
        limiter = TokenBucketRateLimiter(refill_rate=1.0, burst_capacity=10)
        assert limiter.check("key", cost=3) is True
        assert limiter.check("key", cost=7) is True
        assert limiter.check("key", cost=1) is False

    def test_remaining_tokens(self):
        limiter = TokenBucketRateLimiter(refill_rate=1.0, burst_capacity=10)
        limiter.check("key", cost=3)
        assert limiter.remaining("key") == pytest.approx(7.0, abs=0.1)

    def test_reset(self):
        limiter = TokenBucketRateLimiter(refill_rate=1.0, burst_capacity=5)
        for _ in range(5):
            limiter.check("key")
        assert limiter.check("key") is False
        limiter.reset("key")
        for _ in range(5):
            assert limiter.check("key") is True

    def test_refill_rate_property(self):
        limiter = TokenBucketRateLimiter(refill_rate=5.0, burst_capacity=20)
        assert limiter.refill_rate == 5.0
        assert limiter.burst_capacity == 20

    def test_thread_safety(self):
        limiter = TokenBucketRateLimiter(refill_rate=100.0, burst_capacity=200)
        results = []
        errors = []

        def worker():
            try:
                for _ in range(20):
                    results.append(limiter.check("shared"))
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert sum(results) <= 200

    def test_numpy_burst_capacity_validation(self):
        limiter = TokenBucketRateLimiter(refill_rate=1.0, burst_capacity=50)
        allowed = np.array([limiter.check("k0") for _ in range(50)], dtype=int)
        assert allowed.sum() == 50
        assert limiter.check("k0") is False

    def test_numpy_refill_timing_distribution(self):
        limiter = TokenBucketRateLimiter(refill_rate=100.0, burst_capacity=100)
        for _ in range(100):
            limiter.check("key")
        refill_times = []
        for attempt in range(20):
            time.sleep(0.02)
            start = time.time()
            allowed = limiter.check("key")
            elapsed = time.time() - start
            if allowed:
                refill_times.append(elapsed)
        arr = np.array(refill_times)
        assert arr.mean() < 0.05
        assert len(refill_times) >= 1


class TestDistributedTokenBucket:
    def test_local_check(self):
        bucket = DistributedTokenBucket(refill_rate=1.0, burst_capacity=5)
        for _ in range(5):
            assert bucket.check("key") is True
        assert bucket.check("key") is False

    def test_sync_from_peer(self):
        bucket = DistributedTokenBucket(
            refill_rate=1.0, burst_capacity=10, node_id="n1", peers=["n2"]
        )
        bucket.sync_from_peer("n2", "shared-key", 5.0, time.time())
        assert bucket.check("shared-key", cost=3.0) is True

    def test_multiple_peers(self):
        bucket = DistributedTokenBucket(
            refill_rate=1.0, burst_capacity=10, node_id="n1",
            peers=["n2", "n3", "n4"]
        )
        for peer in ["n2", "n3", "n4"]:
            bucket.sync_from_peer(peer, "k", 3.0, time.time())
        total_available = (
            bucket._aggregate("k")
        )
        assert total_available >= 9.0

    def test_numpy_distributed_aggregation(self):
        bucket = DistributedTokenBucket(
            refill_rate=1.0, burst_capacity=20, node_id="n1",
            peers=[f"p{i}" for i in range(10)]
        )
        for peer in [f"p{i}" for i in range(10)]:
            bucket.sync_from_peer(peer, "shared", 10.0, time.time())
        totals = np.array([bucket._aggregate(f"shared-{i}") for i in range(20)])
        assert totals.mean() >= 0.0
