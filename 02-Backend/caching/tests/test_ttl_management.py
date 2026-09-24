import numpy as np

from caching.ttl_management import TTLManager, TTLPolicy


def test_ttl_manager_register_and_remaining():
    manager = TTLManager(policy=TTLPolicy(default_ttl=10.0, max_ttl=100.0, min_ttl=1.0))
    manager.register("key1", ttl=10.0)
    remaining = manager.remaining("key1")
    assert remaining > 0.0
    assert remaining <= 10.0


def test_ttl_manager_default_ttl():
    manager = TTLManager(policy=TTLPolicy(default_ttl=5.0, max_ttl=50.0, min_ttl=1.0))
    manager.register("key1")
    remaining = manager.remaining("key1")
    assert remaining > 0.0
    assert remaining <= 5.0


def test_ttl_manager_expired():
    manager = TTLManager(policy=TTLPolicy(default_ttl=0.0, max_ttl=0.0, min_ttl=0.0))
    manager.register("key1", ttl=0.0)
    assert manager.expired("key1") is True


def test_ttl_manager_expire():
    manager = TTLManager()
    manager.register("key1", ttl=10.0)
    assert manager.expire("key1") is True
    assert manager.expire("key1") is False


def test_ttl_manager_cleanup():
    manager = TTLManager(policy=TTLPolicy(default_ttl=0.0, max_ttl=0.0, min_ttl=0.0))
    manager.register("key1", ttl=0.0)
    manager.register("key2", ttl=0.0)
    cleaned = manager.cleanup()
    assert cleaned == 2
    assert manager.stats()["tracked"] == 0


def test_ttl_manager_stats():
    manager = TTLManager(policy=TTLPolicy(default_ttl=60.0, max_ttl=3600.0, min_ttl=1.0))
    manager.register("key1", ttl=60.0)
    stats = manager.stats()
    assert stats["tracked"] == 1
    assert stats["default_ttl"] == 60.0
