
from retrieval.chunking_strategies import (
    fixed_size_chunk,
    sentence_aware_chunk,
    paragraph_aware_chunk,
    semantic_chunk,
    hierarchical_chunk,
    Chunker,
)
import numpy as np


def test_fixed_size_chunk():
    text = "a" * 250
    chunks = fixed_size_chunk(text, chunk_size=100, overlap=0)
    assert len(chunks) == 3
    assert chunks[0] == "a" * 100


def test_fixed_size_chunk_overlap():
    text = "a" * 250
    chunks = fixed_size_chunk(text, chunk_size=100, overlap=10)
    assert chunks[1] == "a" * 100


def test_sentence_aware_chunk():
    text = "First sentence. Second sentence. Third sentence."
    chunks = sentence_aware_chunk(text, max_chunk_size=50)
    assert all(len(c) <= 50 for c in chunks)
    assert any("First" in c for c in chunks)


def test_sentence_aware_chunk_single():
    text = "Short."
    chunks = sentence_aware_chunk(text)
    assert chunks == ["Short."]


def test_paragraph_aware_chunk():
    text = "Para 1\n\nPara 2\n\nPara 3"
    chunks = paragraph_aware_chunk(text)
    assert len(chunks) == 3
    assert chunks[0] == "Para 1"


def test_paragraph_aware_chunk_single():
    text = "Single para"
    chunks = paragraph_aware_chunk(text)
    assert chunks == ["Single para"]


def test_semantic_chunk():
    text = "First sentence. Second sentence. Third sentence."
    chunks = semantic_chunk(text, similarity_threshold=0.5)
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)


def test_semantic_chunk_single():
    text = "Only one sentence."
    chunks = semantic_chunk(text)
    assert chunks == ["Only one sentence."]


def test_hierarchical_chunk():
    text = "a" * 1000
    result = hierarchical_chunk(text, levels=[200, 500])
    assert "level_1" in result
    assert "level_2" in result


def test_chunker_fixed():
    chunker = Chunker(strategy="fixed", chunk_size=50)
    chunks = chunker.chunk("a" * 120)
    assert len(chunks) == 3


def test_chunker_sentence():
    chunker = Chunker(strategy="sentence", max_chunk_size=50)
    chunks = chunker.chunk("First. Second.")
    assert len(chunks) >= 1


def test_chunker_paragraph():
    chunker = Chunker(strategy="paragraph")
    chunks = chunker.chunk("A\n\nB")
    assert len(chunks) == 2


def test_chunker_semantic():
    chunker = Chunker(strategy="semantic", similarity_threshold=0.5)
    chunks = chunker.chunk("First. Second.")
    assert len(chunks) >= 1


def test_chunker_hierarchical():
    chunker = Chunker(strategy="hierarchical")
    chunks = chunker.chunk("a" * 1000)
    assert len(chunks) >= 1


def test_chunker_unknown():
    chunker = Chunker(strategy="unknown")
    chunks = chunker.chunk("hello")
    assert chunks == ["hello"]
