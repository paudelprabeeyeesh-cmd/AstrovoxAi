import numpy as np
from ai_core.memory_system import MemorySystem, EpisodicMemory, SemanticMemory, WorkingMemoryStore


def test_memory_system_encode_and_retrieve():
    ms = MemorySystem()
    trace_id = ms.encode("hello world", embedding=np.ones(16), importance=0.9)
    assert trace_id.startswith("ep_")
    results = ms.retrieve(np.ones(16), top_k=3)
    assert len(results) <= 3


def test_semantic_memory_concepts():
    sem = SemanticMemory()
    sem.add_concept("cat", embedding=np.array([1.0, 0.0, 0.0] + [0.0] * 13))
    sem.add_concept("dog", embedding=np.array([0.9, 0.1, 0.0] + [0.0] * 13))
    sem.relate("cat", "is_a", "animal")
    related = sem.get_related("cat", "is_a")
    assert "animal" in related
    sim = sem.similarity("cat", "dog")
    assert sim > 0.0


def test_working_memory_store_and_evict():
    wm = WorkingMemoryStore(capacity=3)
    wm.store("a", salience=1.0)
    wm.store("b", salience=0.5)
    wm.store("c", salience=0.2)
    wm.store("d", salience=2.0)
    assert len(wm.get_contents()) <= 3


def test_episodic_memory_capacity_limit():
    ep = EpisodicMemory(capacity=5)
    for i in range(10):
        ep.encode(f"item_{i}", embedding=np.random.randn(16), importance=1.0)
    assert len(ep.traces) <= 5


def test_memory_consolidation():
    ms = MemorySystem()
    for i in range(5):
        ms.encode(f"fact_{i}", embedding=np.random.randn(16), importance=0.5)
    result = ms.consolidate()
    assert result["consolidated"] > 0
    status = ms.get_status()
    assert "episodic_size" in status
