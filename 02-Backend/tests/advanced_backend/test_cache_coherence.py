import time
from advanced_backend.cache_coherence import ConsistencyProtocol


def test_put_get():
    cp = ConsistencyProtocol(consistency="eventual")
    cp.put("k1", "v1", ttl=10, node_id="n1")
    assert cp.get("k1") == "v1"


def test_ttl_expiry():
    cp = ConsistencyProtocol()
    cp.put("k1", "v1", ttl=0.05, node_id="n1")
    time.sleep(0.1)
    assert cp.get("k1") is None


def test_invalidate():
    cp = ConsistencyProtocol()
    cp.put("k1", "v1", ttl=10, node_id="n1")
    cp.invalidate("k1")
    assert cp.get("k1") is None


def test_merge_versions():
    cp = ConsistencyProtocol(consistency="eventual")
    cp.put("k1", "v1", ttl=10, node_id="n1")
    from advanced_backend.cache_coherence import CacheEntry
    incoming = [CacheEntry(key="k1", value="v2", version=5, ttl=10, node_id="n2")]
    cp.merge(incoming)
    assert cp.get("k1") == "v2"


def test_stats():
    cp = ConsistencyProtocol(consistency="strong")
    cp.put("a", 1, ttl=10, node_id="n1")
    stats = cp.stats()
    assert stats["entries"] == 1
    assert stats["consistency"] == "strong"
