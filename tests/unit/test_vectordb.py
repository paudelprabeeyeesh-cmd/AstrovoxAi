"""Tests for vector database and embedding index."""

from __future__ import annotations

import math

import pytest

from astrovox.vectordb import Document, HybridSearchEngine, IncrementalBackup, SnapshotSystem, VectorIndex


def test_vector_index_add_and_search():
    index = VectorIndex()
    index.add(Document(id="1", text="hello", embedding=(1.0, 0.0), metadata={"tag": "a"}))
    index.add(Document(id="2", text="world", embedding=(0.0, 1.0), metadata={"tag": "b"}))
    results = index.search((1.0, 0.0), top_k=1)
    assert len(results) == 1
    assert results[0][0].id == "1"


def test_vector_index_metadata_filter():
    index = VectorIndex()
    index.add(Document(id="1", text="hello", embedding=(1.0, 0.0), metadata={"tag": "a"}))
    index.add(Document(id="2", text="world", embedding=(0.0, 1.0), metadata={"tag": "b"}))
    results = index.search((1.0, 0.0), top_k=2, metadata_filter={"tag": "a"})
    assert len(results) == 1


def test_hybrid_search_upsert_and_query():
    engine = HybridSearchEngine()
    engine.upsert([Document(id="1", text="hello", embedding=(1.0, 0.0))])
    results = engine.query("hello", embedding=(1.0, 0.0), top_k=1)
    assert len(results) == 1
    assert results[0][0].id == "1"


def test_snapshot_system_round_trip(tmp_path):
    system = SnapshotSystem(directory=str(tmp_path))
    index = VectorIndex()
    index.add(Document(id="1", text="hello", embedding=(1.0, 0.0)))
    system.save("snap", index)
    loaded = system.load("snap")
    assert len(loaded) == 1


def test_incremental_backup_flush(tmp_path):
    backup = IncrementalBackup(directory=str(tmp_path))
    backup.record("add", Document(id="1", text="hello", embedding=(1.0, 0.0)))
    path = backup.flush("backup")
    assert path.exists()
    assert path.suffix == ".jsonl"
