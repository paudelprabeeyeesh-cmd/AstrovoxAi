import json

import pytest

from storage.object_store import ObjectStore


@pytest.fixture
def tmp_store(tmp_path):
    return ObjectStore(tmp_path)


def test_put_get(tmp_store):
    tmp_store.put("key1", {"a": 1})
    assert tmp_store.get("key1") == {"a": 1}


def test_get_default(tmp_store):
    assert tmp_store.get("missing", "default") == "default"


def test_exists(tmp_store):
    assert not tmp_store.exists("missing")
    tmp_store.put("present", [1, 2, 3])
    assert tmp_store.exists("present")


def test_delete(tmp_store):
    tmp_store.put("del", "value")
    assert tmp_store.exists("del")
    tmp_store.delete("del")
    assert not tmp_store.exists("del")


def test_keys_and_list(tmp_store):
    tmp_store.put("a", 1)
    tmp_store.put("b", 2)
    keys = tmp_store.keys()
    assert set(keys) == {"a", "b"}
    assert set(tmp_store.list()) == {"a", "b"}


def test_persisted_index(tmp_store):
    tmp_store.put("x", 1)
    path = tmp_store._index_path
    reloaded = ObjectStore(path.parent)
    assert reloaded.exists("x")
    assert reloaded.get("x") == 1
