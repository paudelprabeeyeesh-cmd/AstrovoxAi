import pytest

from storage.metadata_store import MetadataStore


@pytest.fixture
def store(tmp_path):
    return MetadataStore(tmp_path / "meta.db")


def test_set_get(store):
    store.set("color", "blue")
    assert store.get("color") == "blue"


def test_get_default(store):
    assert store.get("missing", 42) == 42


def test_exists(store):
    assert not store.exists("missing")
    store.set("ok", True)
    assert store.exists("ok")


def test_delete(store):
    store.set("x", 1)
    assert store.exists("x")
    store.delete("x")
    assert not store.exists("x")


def test_overwrite(store):
    store.set("k", 1)
    store.set("k", 2)
    assert store.get("k") == 2


def test_all(store):
    store.set("a", 1)
    store.set("b", 2)
    all_meta = store.all()
    assert all_meta == {"a": 1, "b": 2}
