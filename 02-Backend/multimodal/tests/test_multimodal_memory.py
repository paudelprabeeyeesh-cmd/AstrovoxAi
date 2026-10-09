import numpy as np
import pytest

from multimodal.multimodal_memory import (
    CrossModalMemory,
    MemoryEntry,
)


def _make_pixels(h=32, w=32):
    return np.random.randint(0, 255, size=(h, w, 3), dtype=np.uint8)


def _make_mfcc():
    return np.random.randn(13, 40).astype(np.float64)


def test_store_text_returns_id():
    memory = CrossModalMemory(capacity=100, embed_dim=256)
    entry_id = memory.store("text", "hello world", reward=1.0)
    assert entry_id in [e.entry_id for e in memory.memory]


def test_store_image_returns_id():
    memory = CrossModalMemory(capacity=100, embed_dim=256)
    entry_id = memory.store("image", _make_pixels(), reward=0.8)
    assert entry_id in [e.entry_id for e in memory.memory]


def test_store_audio_returns_id():
    memory = CrossModalMemory(capacity=100, embed_dim=256)
    entry_id = memory.store("audio", _make_mfcc(), reward=0.9)
    assert entry_id in [e.entry_id for e in memory.memory]


def test_store_video_returns_id():
    memory = CrossModalMemory(capacity=100, embed_dim=256)
    entry_id = memory.store("video", np.random.randn(128).astype(np.float64), reward=0.7)
    assert entry_id in [e.entry_id for e in memory.memory]


def test_capacity_respects_limit():
    memory = CrossModalMemory(capacity=10, embed_dim=64)
    for i in range(20):
        memory.store("text", f"item {i}")
    assert len(memory.memory) <= 10


def test_sample_experiences_uniform():
    memory = CrossModalMemory(capacity=100, embed_dim=64)
    for i in range(20):
        memory.store("text", f"item {i}", reward=float(i) / 20)
    samples = memory.sample_experiences(batch_size=5, strategy="uniform")
    assert len(samples) == 5
    assert all(isinstance(s, MemoryEntry) for s in samples)


def test_sample_experiences_reward_priority():
    memory = CrossModalMemory(capacity=100, embed_dim=64)
    for i in range(20):
        memory.store("text", f"item {i}", reward=float(i) / 20)
    samples = memory.sample_experiences(batch_size=5, strategy="reward_priority")
    assert len(samples) == 5


def test_sample_experiences_recency():
    memory = CrossModalMemory(capacity=100, embed_dim=64)
    for i in range(20):
        memory.store("text", f"item {i}", reward=float(i) / 20)
    samples = memory.sample_experiences(batch_size=5, strategy="recency")
    assert len(samples) == 5
    assert samples[-1].entry_id == memory.memory[-1].entry_id


def test_replay_returns_list():
    memory = CrossModalMemory(capacity=100, embed_dim=64)
    for i in range(10):
        memory.store("text", f"item {i}", reward=float(i) / 10)
    replayed = memory.replay(batch_size=5)
    assert isinstance(replayed, list)
    assert len(replayed) == 5


def test_consolidate_removes_similar():
    memory = CrossModalMemory(capacity=100, embed_dim=64)
    for i in range(10):
        memory.store("text", "duplicate content", reward=0.5)
    removed = memory.consolidate(threshold=0.9)
    assert removed > 0
    assert len(memory.memory) < 10


def test_retrieve_similar_returns_ranked():
    memory = CrossModalMemory(capacity=100, embed_dim=64)
    memory.store("text", "hello world", reward=1.0)
    memory.store("text", "goodbye world", reward=0.5)
    results = memory.retrieve_similar("text", "hello world", top_k=2)
    assert len(results) <= 2
    assert all(isinstance(r, tuple) and len(r) == 2 for r in results)


def test_unsupported_modality_raises():
    memory = CrossModalMemory(capacity=10, embed_dim=64)
    with pytest.raises(ValueError):
        memory.encode("unknown", "data")
