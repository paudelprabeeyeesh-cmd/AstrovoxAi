"""
Vector database with HNSW indexing for RAG.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    id: str
    vector: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


class HNSWIndex:
    """Hierarchical Navigable Small World index for approximate nearest neighbor search."""

    def __init__(self, dim: int, max_elements: int = 10000, M: int = 16, ef_construction: int = 200):
        self.dim = dim
        self.max_elements = max_elements
        self.M = M
        self.ef_construction = ef_construction
        self.nodes: Dict[str, np.ndarray] = {}
        self.graphs: List[Dict[str, List[str]]] = [{} for _ in range(int(np.log2(max_elements)) + 1)]
        self.entry_point: Optional[str] = None
        self.current_level = 0

    def _distance(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.linalg.norm(a - b))

    def insert(self, id: str, vector: np.ndarray):
        self.nodes[id] = vector
        level = int(random.random() * (self.current_level + 1))
        node_neighbors: Dict[str, List[str]] = {}
        if self.entry_point is None:
            self.entry_point = id
            for layer in self.graphs:
                if level < len(self.graphs):
                    break
                layer[id] = []
            self.current_level = max(self.current_level, level)
            return
        current = self.entry_point
        for lvl in range(self.current_level, level, -1):
            candidates = {current}
            while candidates:
                nearest = min(candidates, key=lambda nid: self._distance(self.nodes[nid], vector))
                if nearest == current and lvl < self.current_level:
                    break
                candidates = set()
                for neighbor in self.graphs[lvl].get(current, []):
                    d = self._distance(self.nodes[neighbor], vector)
                    if d < self._distance(self.nodes[current], vector):
                        candidates.add(neighbor)
                current = nearest
        for lvl in range(min(level, self.current_level) + 1):
            candidates = {current}
            visited = set()
            while candidates:
                nearest = min(candidates, key=lambda nid: self._distance(self.nodes[nid], vector))
                if nearest in visited:
                    break
                visited.add(nearest)
                if self._distance(self.nodes[nearest], vector) < self._distance(self.nodes[current], vector):
                    current = nearest
                for neighbor in self.graphs[lvl].get(current, []):
                    candidates.add(neighbor)
            neighbors = [current]
            for nid in self.graphs[lvl].get(current, []):
                if len(neighbors) >= self.M:
                    break
                neighbors.append(nid)
            neighbors.append(id)
            node_neighbors[id] = neighbors[: self.M]
            self.graphs[lvl][id] = node_neighbors.get(id, [id])
        self.entry_point = id
        self.current_level = max(self.current_level, level)

    def search(self, query: np.ndarray, k: int = 10, ef: int = 50) -> List[Tuple[str, float]]:
        if not self.nodes:
            return []
        candidates = {self.entry_point}
        visited = {self.entry_point}
        results: List[Tuple[str, float]] = [(self.entry_point, self._distance(self.nodes[self.entry_point], query))]
        while candidates:
            nearest = min(candidates, key=lambda nid: self._distance(self.nodes[nid], query))
            candidates.remove(nearest)
            for neighbor in self.graphs[0].get(nearest, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    dist = self._distance(self.nodes[neighbor], query)
                    if len(results) < ef or dist < results[-1][1]:
                        results.append((neighbor, dist))
                        results.sort(key=lambda x: x[1])
                        if len(results) > ef:
                            results = results[:ef]
                    candidates.add(neighbor)
        results.sort(key=lambda x: x[1])
        return results[:k]

    def get_all_ids(self) -> List[str]:
        return list(self.nodes.keys())


class VectorDatabase:
    """Simple vector database with HNSW indexing."""

    def __init__(self, dim: int):
        self.dim = dim
        self.index = HNSWIndex(dim=dim)
        self.records: Dict[str, VectorRecord] = {}

    def upsert(self, records: List[VectorRecord]):
        for record in records:
            self.records[record.id] = record
            self.index.insert(record.id, record.vector)

    def search(self, query_vector: np.ndarray, top_k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None) -> List[VectorRecord]:
        results = self.index.search(query_vector, k=top_k)
        records = []
        for id, dist in results:
            record = self.records.get(id)
            if record is None:
                continue
            if filter_metadata:
                if not all(record.metadata.get(k) == v for k, v in filter_metadata.items()):
                    continue
            records.append(record)
        return records

    def delete(self, id: str):
        self.records.pop(id, None)

    def count(self) -> int:
        return len(self.records)
