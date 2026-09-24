import numpy as np

from caching.semantic_cache import SemanticCache


def test_semantic_cache_exact_match():
    cache = SemanticCache(max_entries=10, similarity_threshold=0.99)
    cache.set("k1", "value1", "hello world")
    result = cache.get("hello world")
    assert result == "value1"


def test_semantic_cache_miss():
    cache = SemanticCache(max_entries=10, similarity_threshold=0.99)
    assert cache.get("hello world") is None


def test_semantic_cache_similar_match():
    np.random.seed(42)
    cache = SemanticCache(max_entries=10, similarity_threshold=0.5)
    cache.set("k1", "v1", "alpha beta gamma")
    result = cache.get("alpha beta delta")
    assert result == "v1"


def test_semantic_cache_delete():
    cache = SemanticCache(max_entries=10)
    cache.set("k1", "v1", "hello world")
    assert cache.delete("k1") is True
    assert cache.delete("k1") is False
    assert cache.get("hello world") is None


def test_semantic_cache_clear():
    cache = SemanticCache(max_entries=10)
    cache.set("k1", "v1", "hello world")
    cache.set("k2", "v2", "goodbye world")
    cache.clear()
    assert cache.get("hello world") is None
    assert cache.get("goodbye world") is None
    assert cache.stats()["entries"] == 0


def test_semantic_cache_eviction():
    cache = SemanticCache(max_entries=2)
    cache.set("k1", "v1", "one")
    cache.set("k2", "v2", "two")
    cache.set("k3", "v3", "three")
    assert cache.stats()["entries"] <= 2


def test_semantic_cache_stats():
    cache = SemanticCache(max_entries=10)
    cache.set("k1", "v1", "hello")
    stats = cache.stats()
    assert stats["entries"] == 1
    assert stats["similarity_threshold"] == 0.9
