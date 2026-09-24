import time
import pytest
from production_readiness.caching_advanced import MultiTierCache, CacheLevel, CacheEntry, CacheWarming


def test_multi_tier_cache_set_get():
    cache = MultiTierCache()
    cache.set("key-1", "value-1", 60.0)
    assert cache.get("key-1") == "value-1"


def test_multi_tier_cache_miss():
    cache = MultiTierCache()
    assert cache.get("missing") is None


def test_multi_tier_cache_delete():
    cache = MultiTierCache()
    cache.set("key-1", "value-1", 60.0)
    cache.delete("key-1")
    assert cache.get("key-1") is None


def test_multi_tier_cache_stats():
    cache = MultiTierCache()
    cache.set("key-1", "value-1", 60.0)
    assert cache.get("key-1") == "value-1"
    stats = cache.stats()
    assert stats["total_hits"] > 0


def test_cache_entry_expired():
    import pytest
    from production_readiness.caching_advanced import CacheEntry
    entry = CacheEntry(key="k", value="v", ttl=0.1)
    assert entry.expired() is False
    time.sleep(0.2)
    assert entry.expired() is True


def test_cache_clears():
    cache = MultiTierCache()
    cache.set("key-1", "value-1", 60.0)
    cache.clear()
    assert cache.get("key-1") is None


def test_cache_warming():
    cache = MultiTierCache()
    warming = CacheWarming(cache)
    warming.register(lambda: [("key-1", "value-1", 60.0)])
    result = warming.warm()
    assert result["warmed"] == 1
    assert cache.get("key-1") == "value-1"
