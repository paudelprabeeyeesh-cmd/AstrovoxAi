import pytest
from app.memory import create_memory, list_memories, search_memories, delete_memory

def test_create_and_list():
    m = create_memory("u1", type("obj", (object,), {"key": "k", "value": "v"})())
    assert m.key == "k"
    all_m = list_memories("u1")
    assert len(all_m) >= 1

def test_search():
    results = search_memories("u1", "k")
    assert len(results) >= 1

def test_delete():
    delete_memory("u1")
    results = search_memories("u1", "k")
    assert len(results) == 0
