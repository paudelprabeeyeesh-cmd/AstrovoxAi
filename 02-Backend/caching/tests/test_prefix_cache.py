import numpy as np

from caching.prefix_cache import PrefixCache


def test_prefix_cache_set_and_get():
    cache = PrefixCache(max_entries=10)
    cache.set("users", "u1", {"id": 1})
    result = cache.get("users", "u1")
    assert result == {"id": 1}


def test_prefix_cache_get_miss():
    cache = PrefixCache(max_entries=10)
    assert cache.get("users", "u1") is None


def test_prefix_cache_get_by_prefix():
    cache = PrefixCache(max_entries=10)
    cache.set("users", "u1", {"id": 1})
    cache.set("users", "u2", {"id": 2})
    results = cache.get_by_prefix("users")
    assert len(results) == 2
    assert {"id": 1} in results
    assert {"id": 2} in results


def test_prefix_cache_invalidate_prefix():
    cache = PrefixCache(max_entries=10)
    cache.set("users", "u1", {"id": 1})
    cache.set("items", "i1", {"id": 1})
    removed = cache.invalidate_prefix("users")
    assert removed == 1
    assert cache.get("users", "u1") is None
    assert cache.get("items", "i1") is not None


def test_prefix_cache_delete():
    cache = PrefixCache(max_entries=10)
    cache.set("users", "u1", {"id": 1})
    assert cache.delete("users", "u1") is True
    assert cache.delete("users", "u1") is False


def test_prefix_cache_eviction():
    cache = PrefixCache(max_entries=2)
    cache.set("a", "1", {})
    cache.set("b", "2", {})
    cache.set("c", "3", {})
    assert cache.stats()["entries"] <= 2


def test_prefix_cache_stats():
    cache = PrefixCache(max_entries=10)
    cache.set("users", "u1", {"id": 1})
    stats = cache.stats()
    assert stats["entries"] == 1
    assert stats["prefixes"] == 1
