from __future__ import annotations

import pytest
import numpy as np

from memory_persistence.memory_extraction import MemoryExtractor


@pytest.fixture
def extractor():
    return MemoryExtractor(importance_threshold=0.2)


def test_score_noise(extractor):
    score, category = extractor.score("hi")
    assert category == "noise"
    assert score == 0.0


def test_score_fact(extractor):
    score, category = extractor.score("My name is Alice and I live in Paris")
    assert category == "identity"
    assert score > 0.0


def test_score_preference(extractor):
    score, category = extractor.score("I love hiking and my favorite food is pasta")
    assert category == "preference"
    assert score > 0.0


def test_score_general(extractor):
    score, category = extractor.score("The quick brown fox jumps over the lazy dog")
    assert category == "general"
    assert score >= 0.0


def test_extract_returns_memory(extractor):
    memory = extractor.extract("t1", "My name is Alice and my phone is 555-1234")
    assert memory is not None
    assert memory.source_turn_id == "t1"
    assert memory.category == "identity"


def test_extract_returns_none_for_noise(extractor):
    assert extractor.extract("t1", "hello") is None


def test_batch_extract(extractor):
    turns = [
        ("t1", "hello", None),
        ("t2", "My name is Carol and my phone is 555-1234", None),
        ("t3", "thanks", None),
    ]
    memories = extractor.batch_extract(turns)
    assert len(memories) == 1
    assert memories[0].source_turn_id == "t2"


def test_extract_metadata(extractor):
    memory = extractor.extract("t1", "I work at Acme Corp and my email is test@example.com", {"source": "chat"})
    assert memory.metadata == {"source": "chat"}
    assert memory.category == "identity"
