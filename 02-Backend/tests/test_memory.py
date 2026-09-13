import pytest
from app.memory import create_memory, list_memories, search_memories, delete_memory

class DummyMemory:
    def __init__(self, key, value):
        self.key = key
        self.value = value
    def dict(self):
        return {"key": self.key, "value": self.value}

def test_create_and_list():
    m = create_memory("u1", DummyMemory("k", "v"))
    assert m.key == "k"
    all_m = list_memories("u1")
    assert len(all_m) >= 1

def test_search():
    results = search_memories("u1", "k")
    assert len(results) >= 1

def test_delete():
    results = search_memories("u1", "k")
    for m in results:
        delete_memory(m.id, "u1")
    results = search_memories("u1", "k")
    assert len(results) == 0
