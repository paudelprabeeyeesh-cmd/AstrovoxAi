from cache_coherence.coherence_protocol import CoherenceProtocol, CacheEntry
from cache_coherence.invalidation_service import InvalidationService
from cache_coherence.replication_tracker import ReplicationTracker
from cache_coherence.version_vector import VersionVector


def _make_protocol(node_id: str = "node-a") -> CoherenceProtocol:
    return CoherenceProtocol(node_id=node_id)


def test_put_and_get():
    proto = _make_protocol()
    entry = proto.put("key-1", "value-1")
    assert entry is not None
    assert proto.get("key-1") == "value-1"


def test_get_nonexistent_returns_none():
    proto = _make_protocol()
    assert proto.get("missing") is None


def test_put_overwrites_value():
    proto = _make_protocol()
    proto.put("key-1", "old")
    proto.put("key-1", "new")
    assert proto.get("key-1") == "new"


def test_invalidate_key():
    proto = _make_protocol()
    proto.put("key-1", "value-1")
    proto.invalidate_key("key-1", "source-node")
    assert proto.get("key-1") is None


def test_invalidate_all():
    proto = _make_protocol()
    proto.put("key-1", "v1")
    proto.put("key-2", "v2")
    keys = proto.invalidate_all("source-node")
    assert proto.get("key-1") is None
    assert proto.get("key-2") is None
    assert "key-1" in keys


def test_stats():
    proto = _make_protocol()
    proto.put("key-1", "v1")
    proto.put("key-2", "v2")
    proto.invalidate_key("key-2", "s")
    stats = proto.stats()
    assert stats["total_entries"] == 2
    assert stats["valid_entries"] == 1
    assert stats["invalidated_entries"] == 1


def test_snapshot():
    proto = _make_protocol()
    proto.put("key-1", "v1")
    snap = proto.snapshot()
    assert snap["node_id"] == "node-a"
    assert "key-1" in snap["entries"]


def test_check_coherence():
    proto = _make_protocol()
    proto.put("key-1", "v1")
    assert proto.check_coherence("key-1") is True
    proto.invalidate_key("key-1", "s")
    assert proto.check_coherence("key-1") is False
    assert proto.check_coherence("missing") is True


def test_merge_from_new_remote_key():
    proto = _make_protocol()
    remote_entry = CacheEntry(key="remote-key", value="rv", version_vector=VersionVector.from_dict({"node-b": 3}))
    proto.merge_from({"remote-key": remote_entry})
    assert proto.get("remote-key") == "rv"


def test_merge_from_invalidated_remote_key():
    proto = _make_protocol()
    proto.put("key-1", "v1")
    remote = CacheEntry(key="key-1", value="rv", version_vector=VersionVector.from_dict({"node-b": 5}))
    remote.invalidated = True
    proto.merge_from({"key-1": remote})
    assert proto.get("key-1") == "v1"


def test_on_remote_put_remote_wins():
    proto = _make_protocol()
    proto.put("key-1", "local")
    remote = CacheEntry(key="key-1", value="remote", version_vector=VersionVector.from_dict({"node-b": 5}))
    proto.on_remote_put(remote)
    assert proto.get("key-1") == "remote"


def test_custom_dependencies():
    inv_service = InvalidationService()
    rep_tracker = ReplicationTracker("node-a")
    proto = CoherenceProtocol(
        node_id="node-a",
        invalidation_service=inv_service,
        replication_tracker=rep_tracker,
    )
    proto.put("key-1", "v1")
    proto.invalidate_key("key-1", "source")
    assert inv_service.is_invalidated("key-1") is True
    assert rep_tracker.is_replicated("key-1", "node-a") is True


def test_put_increments_version_vector():
    proto = _make_protocol()
    entry = proto.put("key-1", "v1")
    assert entry.version_vector._clock["node-a"] == 1


def test_merge_from_keeps_local_when_local_dominates_remote():
    proto = _make_protocol()
    proto.put("key-1", "local")
    remote = CacheEntry(key="key-1", value="remote", version_vector=VersionVector.from_dict({"node-b": 1}))
    proto.merge_from({"key-1": remote})
    assert proto.get("key-1") == "local"


def test_merge_from_replaces_when_remote_dominates_and_valid():
    proto = _make_protocol()
    proto.put("key-1", "local")
    remote = CacheEntry(key="key-1", value="remote", version_vector=VersionVector.from_dict({"node-a": 2}))
    proto.merge_from({"key-1": remote})
    assert proto.get("key-1") == "remote"


def test_merge_from_concurrent_keeps_remote():
    proto = _make_protocol()
    proto.put("key-1", "local")
    remote = CacheEntry(key="key-1", value="remote", version_vector=VersionVector.from_dict({"node-b": 1}))
    proto.merge_from({"key-1": remote})
    assert proto.get("key-1") == "remote"


def test_merge_from_both_invalidated_keeps_local():
    proto = _make_protocol()
    proto.put("key-1", "local")
    remote = CacheEntry(key="key-1", value="remote", version_vector=VersionVector.from_dict({"node-a": 2}))
    remote.invalidated = True
    proto.merge_from({"key-1": remote})
    assert proto.get("key-1") is None


def test_on_remote_put_keeps_local_when_local_dominates():
    proto = _make_protocol()
    proto.put("key-1", "local")
    local_entry = proto._entries["key-1"]
    local_entry.version_vector._clock["node-a"] = 5
    remote = CacheEntry(key="key-1", value="remote", version_vector=VersionVector.from_dict({"node-a": 2}))
    proto.on_remote_put(remote)
    assert proto.get("key-1") == "local"


def test_on_remote_put_replaces_when_concurrent():
    proto = _make_protocol()
    proto.put("key-1", "local")
    remote = CacheEntry(key="key-1", value="remote", version_vector=VersionVector.from_dict({"node-b": 1}))
    proto.on_remote_put(remote)
    assert proto.get("key-1") == "remote"


def test_on_remote_put_adds_new_entry():
    proto = _make_protocol()
    remote = CacheEntry(key="remote-key", value="rv", version_vector=VersionVector.from_dict({"node-b": 3}))
    proto.on_remote_put(remote)
    assert proto.get("remote-key") == "rv"
