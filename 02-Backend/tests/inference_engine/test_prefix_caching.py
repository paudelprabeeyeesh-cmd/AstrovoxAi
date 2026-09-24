import numpy as np

from inference_engine.prefix_caching import (
    PrefixCache,
    CacheEntry,
)


def test_prefix_cache_lookup_miss():
    cache = PrefixCache(max_entries=10)
    result = cache.lookup((1, 2, 3))
    assert result is None
    assert cache.stats["misses"] == 1


def test_prefix_cache_insert_and_lookup():
    cache = PrefixCache(max_entries=10)
    tokens = (1, 2, 3, 4, 5)
    kv = np.random.randn(5, 4, 32).astype(np.float32)
    entry = cache.insert(tokens, kv)
    assert entry is not None
    result = cache.lookup(tokens)
    assert result is not None
    found_entry, overlap = result
    assert overlap == 5
    assert cache.stats["hits"] == 1


def test_prefix_cache_best_prefix():
    cache = PrefixCache(max_entries=10)
    cache.insert((1, 2, 3), np.random.randn(3, 4, 32).astype(np.float32))
    cache.insert((1, 2, 3, 4, 5), np.random.randn(5, 4, 32).astype(np.float32))
    result = cache.find_best_prefix((1, 2, 3, 4, 5, 6))
    assert result is not None
    entry, length = result
    assert length == 5


def test_prefix_cache_invalidate():
    cache = PrefixCache(max_entries=10)
    tokens = (1, 2, 3)
    cache.insert(tokens, np.random.randn(3, 4, 32).astype(np.float32))
    cache.invalidate(tokens)
    result = cache.lookup(tokens)
    assert result is None
    assert cache.stats["invalidations"] == 1


def test_prefix_cache_invalidate_all():
    cache = PrefixCache(max_entries=10)
    cache.insert((1, 2, 3), np.random.randn(3, 4, 32).astype(np.float32))
    cache.insert((1, 2, 3, 4), np.random.randn(4, 4, 32).astype(np.float32))
    cache.insert((5, 6, 7), np.random.randn(3, 4, 32).astype(np.float32))
    cache.invalidate_all((1, 2, 3))
    assert cache.lookup((1, 2, 3)) is None
    assert cache.lookup((1, 2, 3, 4)) is None
    assert cache.lookup((5, 6, 7)) is not None


def test_prefix_cache_eviction():
    cache = PrefixCache(max_entries=2, max_size_bytes=1024)
    for i in range(5):
        cache.insert((i,), np.random.randn(1, 4, 32).astype(np.float32))
    assert len(cache.cache) <= 2


def test_prefix_cache_stats():
    cache = PrefixCache(max_entries=10)
    cache.insert((1, 2), np.random.randn(2, 4, 32).astype(np.float32))
    cache.lookup((1, 2))
    cache.lookup((1, 2))
    stats = cache.get_stats()
    assert stats["hits"] == 2
    assert stats["entries"] == 1


def test_prefix_cache_find_best_prefix_no_match():
    cache = PrefixCache(max_entries=10)
    cache.insert((1, 2, 3), np.random.randn(3, 4, 32).astype(np.float32))
    result = cache.find_best_prefix((4, 5, 6))
    assert result is None
    assert cache.stats["misses"] == 1


def test_cache_entry_defaults():
    entry = CacheEntry(cache_key="abc", token_ids=(1, 2), kv_data=None)
    assert entry.hit_count == 0
    assert entry.is_valid is True
    assert entry.version == 0
