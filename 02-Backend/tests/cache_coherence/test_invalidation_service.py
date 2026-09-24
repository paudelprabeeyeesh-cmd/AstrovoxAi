from cache_coherence.invalidation_service import InvalidationService


def _make_service() -> InvalidationService:
    return InvalidationService()


def test_invalidate_key():
    svc = _make_service()
    svc.invalidate("key-1", "source-node")
    assert svc.is_invalidated("key-1") is True


def test_is_invalidated_false():
    svc = _make_service()
    assert svc.is_invalidated("key-1") is False


def test_acknowledge():
    svc = _make_service()
    svc.invalidate("key-1", "source")
    svc.acknowledge("key-1", "node-b")
    assert svc.pending_acks() == {}


def test_invalidate_with_ack():
    svc = _make_service()
    nodes = {"node-b", "node-c"}
    svc.invalidate_with_ack("key-1", "source", nodes)
    pending = svc.pending_acks()
    assert "key-1" in pending
    assert "node-b" in pending["key-1"]
    assert "node-c" in pending["key-1"]


def test_record_write_removes_from_invalidated():
    svc = _make_service()
    svc.invalidate("key-1", "source")
    assert svc.is_invalidated("key-1") is True
    svc.record_write("key-1", "node-b")
    assert svc.is_invalidated("key-1") is False


def test_invalidate_all_clears():
    svc = _make_service()
    svc.invalidate("key-1", "s")
    svc.invalidate("key-2", "s")
    svc.invalidate_all("s")
    assert svc.is_invalidated("key-1") is False
    assert svc.is_invalidated("key-2") is False


def test_history():
    svc = _make_service()
    svc.invalidate("key-1", "source")
    svc.invalidate("key-1", "source")
    history = svc.history("key-1")
    assert len(history) == 2


def test_stats():
    svc = _make_service()
    svc.invalidate("key-1", "s")
    svc.invalidate("key-2", "s")
    stats = svc.stats()
    assert stats["invalidated_keys"] == 2
    assert stats["history_keys"] == 2


def test_cleanup():
    svc = _make_service()
    svc.invalidate("key-1", "s")
    cleaned = svc.cleanup(max_age=0.0)
    assert cleaned == 1
    assert svc.is_invalidated("key-1") is False
