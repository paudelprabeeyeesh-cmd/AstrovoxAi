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


def test_vector_index_search_returns_sorted():
    index = VectorIndex()
    for i in range(5):
        index.add(Document(id=str(i), text=f"doc{i}", embedding=_embed(f"doc{i}")))
    query = _embed("doc0")
    results = index.search(query, top_k=5)
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_hybrid_search_metadata_filter_multiple():
    engine = HybridSearchEngine()
    engine.upsert([
        Document(id="1", text="a", embedding=(1.0, 0.0), metadata={"tag": "x"}),
        Document(id="2", text="b", embedding=(0.0, 1.0), metadata={"tag": "y"}),
    ])
    results = engine.query("a", embedding=(1.0, 0.0), top_k=2, metadata_filter={"tag": "x"})
    assert len(results) == 1
    assert results[0][0].id == "1"


def test_snapshot_system_save_creates_file(tmp_path):
    system = SnapshotSystem(directory=str(tmp_path))
    index = VectorIndex()
    index.add(Document(id="1", text="hello", embedding=(1.0, 0.0)))
    path = system.save("snap1", index)
    assert path.exists()


def test_incremental_backup_multiple_records(tmp_path):
    backup = IncrementalBackup(directory=str(tmp_path))
    for i in range(3):
        backup.record("add" if i % 2 == 0 else "remove", Document(id=str(i), text=f"t{i}", embedding=(1.0, 0.0)))
    path = backup.flush("backup1")
    assert path.exists()
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 3
