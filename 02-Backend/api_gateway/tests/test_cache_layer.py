import time
import threading
import pytest
from api_gateway.cache_layer import (
    CacheLayer,
    CacheLayerProxy,
    CacheEntry,
)


class TestCacheLayer:
    def test_set_and_get(self):
        cache = CacheLayer(max_size=10, default_ttl=60.0)
        cache.set("k1", "v1")
        assert cache.get("k1") == "v1"

    def test_get_missing_returns_none(self):
        cache = CacheLayer()
        assert cache.get("missing") is None

    def test_get_missing_returns_default(self):
        cache = CacheLayer()
        assert cache.get("missing", "fallback") == "fallback"

    def test_set_ttl_expiry(self):
        cache = CacheLayer(default_ttl=0.05)
        cache.set("k1", "v1", ttl=0.05)
        assert cache.get("k1") == "v1"
        time.sleep(0.1)
        assert cache.get("k1") is None

    def test_override_ttl(self):
        cache = CacheLayer(default_ttl=100.0)
        cache.set("k1", "v1", ttl=0.05)
        time.sleep(0.1)
        assert cache.get("k1") is None

    def test_overwrite_existing(self):
        cache = CacheLayer()
        cache.set("k1", "v1")
        cache.set("k1", "v2")
        assert cache.get("k1") == "v2"

    def test_delete(self):
        cache = CacheLayer()
        cache.set("k1", "v1")
        assert cache.delete("k1") is True
        assert cache.get("k1") is None
        assert cache.delete("k1") is False

    def test_exists(self):
        cache = CacheLayer()
        cache.set("k1", "v1")
        assert cache.exists("k1") is True
        assert cache.exists("missing") is False

    def test_clear(self):
        cache = CacheLayer()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.size == 0
        assert cache.get("k1") is None

    def test_max_size_eviction(self):
        cache = CacheLayer(max_size=3)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")
        cache.set("k4", "v4")
        assert cache.size <= 3

    def test_ttl_eviction(self):
        cache = CacheLayer(max_size=1000, default_ttl=0.05)
        cache.set("k1", "v1", ttl=0.05)
        cache.set("k2", "v2", ttl=0.05)
        assert cache.size == 2
        time.sleep(0.1)
        assert cache.size == 0

    def test_tags(self):
        cache = CacheLayer()
        cache.set("k1", "v1", tags=("user:1", "session:abc"))
        cache.set("k2", "v2", tags=("user:2", "session:xyz"))
        assert cache.invalidate_by_tag("user:1") == 1

    def test_invalidate_by_tag_all(self):
        cache = CacheLayer()
        cache.set("k1", "v1", tags=("t1",))
        cache.set("k2", "v2", tags=("t1",))
        cache.set("k3", "v3", tags=("t2",))
        assert cache.invalidate_by_tag("t1") == 2
        assert cache.size == 1

    def test_stats_hit_rate(self):
        cache = CacheLayer()
        cache.set("k1", "v1")
        cache.get("k1")
        cache.get("missing")
        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_stats_size(self):
        cache = CacheLayer(max_size=10)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        assert cache.stats["size"] == 2

    def test_clear_stats(self):
        cache = CacheLayer()
        cache.set("k1", "v1")
        cache.get("k1")
        cache.clear()
        stats = cache.stats
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_set_many(self):
        cache = CacheLayer()
        cache.set_many({"k1": ("v1", 0.0, ()), "k2": ("v2", 0.0, ())})
        assert cache.get("k1") == "v1"
        assert cache.get("k2") == "v2"

    def test_get_many(self):
        cache = CacheLayer()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        result = cache.get_many(["k1", "k2", "k3"])
        assert result["k1"] == "v1"
        assert result["k2"] == "v2"
        assert result["k3"] is None

    def test_concurrent_access(self):
        cache = CacheLayer(max_size=1000)
        errors = []

        def worker(i):
            try:
                for j in range(100):
                    cache.set(f"k{i}-{j}", j)
                    cache.get(f"k{i}-{j % 10}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0

    def test_cache_entry_dataclass(self):
        entry = CacheEntry(value="v", created_at=time.time(), ttl=10.0)
        assert entry.value == "v"
        assert entry.hit_count == 0

    def test_proxy_set_and_get(self):
        cache = CacheLayer()
        proxy = CacheLayerProxy(cache, prefix="user:")
        proxy.set("1", "alice")
        assert proxy.get("1") == "alice"
        assert cache.get("user:1") == "alice"

    def test_proxy_delete(self):
        cache = CacheLayer()
        proxy = CacheLayerProxy(cache, prefix="user:")
        proxy.set("1", "alice")
        assert proxy.delete("1") is True
        assert proxy.get("1") is None

    def test_size_tracks_correctly(self):
        cache = CacheLayer()
        cache.set("k1", "v1")
        assert cache.size == 1
        cache.set("k2", "v2")
        assert cache.size == 2
        cache.delete("k1")
        assert cache.size == 1
