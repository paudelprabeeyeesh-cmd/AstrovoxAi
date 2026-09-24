from cache_coherence.replication_tracker import ReplicationTracker


def _make_tracker(node_id: str = "node-a") -> ReplicationTracker:
    return ReplicationTracker(node_id=node_id)


def test_record_write():
    rt = _make_tracker()
    rt.record_write("key-1", "node-a")
    assert rt.is_replicated("key-1", "node-a") is True


def test_nodes_for_key():
    rt = _make_tracker()
    rt.record_write("key-1", "node-a")
    rt.replicate_to("key-1", "node-a", {"node-b", "node-c"})
    nodes = rt.nodes_for_key("key-1")
    assert "node-a" in nodes
    assert "node-b" in nodes
    assert "node-c" in nodes


def test_replicate_to():
    rt = _make_tracker()
    rt.replicate_to("key-1", "node-a", {"node-b"})
    event = rt.incomplete_events()
    assert len(event) == 1
    assert event[0].key == "key-1"
    assert event[0].source_node == "node-a"
    assert "node-b" in event[0].target_nodes


def test_acknowledge_replica_completes_event():
    rt = _make_tracker()
    rt.replicate_to("key-1", "node-a", {"node-b"})
    assert len(rt.incomplete_events()) == 1
    rt.acknowledge_replica("key-1", "node-b")
    assert len(rt.incomplete_events()) == 0


def test_on_invalidation_marks_completed():
    rt = _make_tracker()
    rt.replicate_to("key-1", "node-a", {"node-b"})
    assert len(rt.incomplete_events()) == 1
    rt.on_invalidation("key-1", "node-a")
    assert len(rt.incomplete_events()) == 0


def test_stats():
    rt = _make_tracker()
    rt.record_write("key-1", "node-a")
    rt.replicate_to("key-2", "node-a", {"node-b"})
    stats = rt.stats()
    assert stats["tracked_keys"] == 2
    assert stats["incomplete_replications"] == 1


def test_is_not_replicated():
    rt = _make_tracker()
    assert rt.is_replicated("key-1", "node-a") is False


def test_nodes_for_key_empty():
    rt = _make_tracker()
    assert rt.nodes_for_key("key-1") == set()
