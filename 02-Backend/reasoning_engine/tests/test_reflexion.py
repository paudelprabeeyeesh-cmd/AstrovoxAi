import numpy as np
from reasoning_engine.reflexion import ReflexionMemory


def test_store_and_retrieve():
    mem = ReflexionMemory(embedding_dim=8)
    mem.store_failure(task="t1", error="e1", trace="trace1", reflection="reflect1")
    assert mem.size() == 1
    results = mem.retrieve_similar("t1", top_k=1)
    assert len(results) == 1
    assert results[0]["reflection"] == "reflect1"


def test_retrieve_empty():
    mem = ReflexionMemory()
    assert mem.retrieve_similar("anything") == []


def test_inject_into_context_no_memories():
    mem = ReflexionMemory()
    ctx = "Context here"
    new_ctx = mem.inject_into_context("task", ctx)
    assert new_ctx == ctx


def test_inject_into_context_with_memories():
    mem = ReflexionMemory(embedding_dim=4)
    mem.store_failure(task="t1", error="err", trace="t", reflection="don't repeat")
    mem.store_failure(task="t2", error="err2", trace="t2", reflection="avoid this")
    ctx = "Original context"
    new_ctx = mem.inject_into_context("t1", ctx, top_k=2)
    assert "Past reflections" in new_ctx
    assert "Original context" in new_ctx


def test_multiple_storages_order():
    mem = ReflexionMemory(embedding_dim=8)
    for i in range(5):
        mem.store_failure(task=f"task{i}", error=f"e{i}", trace=f"t{i}", reflection=f"r{i}")
    assert mem.size() == 5
    results = mem.retrieve_similar("task0", top_k=2)
    assert len(results) <= 2


def test_embedding_dimension():
    mem = ReflexionMemory(embedding_dim=32)
    mem.store_failure("t", "e", "trace", "ref")
    emb = mem.memories[0]["embedding"]
    assert emb.shape == (32,)
    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 1e-6


def test_retrieve_top_k_respected():
    mem = ReflexionMemory(embedding_dim=8)
    for i in range(10):
        mem.store_failure(task=f"t{i}", error=f"e{i}", trace=f"trace{i}", reflection=f"r{i}")
    results = mem.retrieve_similar("t0", top_k=3)
    assert len(results) <= 3
