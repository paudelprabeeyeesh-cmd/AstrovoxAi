"""Tests for vector database - expanded coverage."""

from __future__ import annotations

import math

import numpy as np
import pytest

from astrovox.vectordb import Document, HybridSearchEngine, IncrementalBackup, SnapshotSystem, VectorIndex


def _embed(text: str) -> tuple:
    vec = np.random.default_rng(hash(text) % 2**32).standard_normal(16)
    vec = vec / np.linalg.norm(vec)
    return tuple(vec.astype(float).tolist())


def test_vector_index_add_many():
    index = VectorIndex()
    docs = [Document(id=str(i), text=f"doc{i}", embedding=_embed(f"doc{i}")) for i in range(20)]
    index.add_many(docs)
    assert len(index) == 20


def test_vector_index_remove():
    index = VectorIndex()
    index.add(Document(id="1", text="hello", embedding=_embed("hello")))
    index.remove("1")
    assert len(index) == 0


def test_vector_index_search_top_k():
    index = VectorIndex()
    for i in range(10):
        index.add(Document(id=str(i), text=f"doc{i}", embedding=_embed(f"doc{i}")))
    query = _embed("doc0")
    results = index.search(query, top_k=3)
    assert len(results) == 3


def test_vector_index_search_empty_returns_empty():
    index = VectorIndex()
    results = index.search(_embed("missing"), top_k=1)
    assert results == []


def test_hybrid_search_empty_index():
    engine = HybridSearchEngine()
    results = engine.query("anything", embedding=_embed("anything"), top_k=1)
    assert results == []


def test_snapshot_system_missing_file(tmp_path):
    system = SnapshotSystem(directory=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        system.load("missing")


def test_incremental_backup_records_operations():
    backup = IncrementalBackup(directory="test_backups")
    backup.record("add", Document(id="1", text="hello", embedding=(1.0, 0.0)))
    backup.record("remove", Document(id="2", text="world", embedding=(0.0, 1.0)))
    assert len(backup._log) == 2


def test_document_with_metadata():
    doc = Document(id="1", text="hello", embedding=(1.0, 0.0), metadata={"tag": "a"})
    assert doc.metadata["tag"] == "a"


def test_vector_index_len_zero():
    index = VectorIndex()
    assert len(index) == 0
