
from caching.api_response_cache import APIResponseCache


def test_api_response_cache_set_and_get():
    cache = APIResponseCache(max_entries=10)
    value = cache.set("GET", "/api/v1/users", {"page": "1"}, value={"users": []}, ttl=60.0)
    assert value is not None
    result = cache.get("GET", "/api/v1/users", {"page": "1"})
    assert result == {"users": []}


def test_api_response_cache_miss():
    cache = APIResponseCache(max_entries=10)
    result = cache.get("GET", "/api/v1/users", {"page": "1"})
    assert result is None


def test_api_response_cache_invalidate_tag():
    cache = APIResponseCache(max_entries=10)
    cache.set("GET", "/api/v1/users", {"page": "1"}, value={}, ttl=60.0, tags=["users"])
    cache.set("GET", "/api/v1/items", {"page": "1"}, value={}, ttl=60.0, tags=["items"])
    removed = cache.invalidate_tag("users")
    assert removed == 1
    assert cache.get("GET", "/api/v1/users", {"page": "1"}) is None
    assert cache.get("GET", "/api/v1/items", {"page": "1"}) is not None


def test_api_response_cache_invalidate_prefix():
    cache = APIResponseCache(max_entries=10)
    entry1 = cache.set("GET", "/api/v1/users", {"page": "1"}, value={}, ttl=60.0)
    cache.set("GET", "/api/v1/items", {"page": "1"}, value={}, ttl=60.0)
    prefix = entry1.key[:8]
    removed = cache.invalidate_prefix(prefix)
    assert removed >= 1


def test_api_response_cache_stats():
    cache = APIResponseCache(max_entries=10)
    cache.set("GET", "/api/v1/users", {"page": "1"}, value={}, ttl=60.0)
    stats = cache.stats()
    assert stats["entries"] == 1
    assert stats["max_entries"] == 10


def test_api_response_cache_eviction():
    cache = APIResponseCache(max_entries=2)
    cache.set("GET", "/api/v1/a", {"page": "1"}, value={}, ttl=60.0)
    cache.set("GET", "/api/v1/b", {"page": "1"}, value={}, ttl=60.0)
    cache.set("GET", "/api/v1/c", {"page": "1"}, value={}, ttl=60.0)
    assert cache.stats()["entries"] <= 2
