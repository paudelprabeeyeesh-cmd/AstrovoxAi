"""Vector database for RAG pipelines with HNSW indexing and metadata filtering."""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    content: str = ""


@dataclass
class SearchResult:
    record: VectorRecord
    score: float
    rank: int = 0


class HNSWIndex:
    """Hierarchical Navigable Small World index for approximate nearest neighbor search."""

    def __init__(self, dim: int, max_elements: int = 10000, M: int = 16, ef_construction: int = 200):
        self.dim = dim
        self.max_elements = max_elements
        self.M = M
        self.ef_construction = ef_construction
        self.nodes: Dict[str, List[float]] = {}
        self.graphs: List[Dict[str, List[str]]] = [{} for _ in range(int(math.log2(max_elements)) + 1)]
        self.entry_point: Optional[str] = None
        self.current_level = 0

    def _distance(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def insert(self, id: str, vector: List[float]):
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

    def search(self, query: List[float], k: int = 10, ef: int = 50) -> List[Tuple[str, float]]:
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


class VectorStore:
    """Vector database with HNSW indexing, metadata filtering, and CRUD operations."""

    def __init__(self, dim: int):
        self.dim = dim
        self.index = HNSWIndex(dim=dim)
        self.records: Dict[str, VectorRecord] = {}

    def upsert(self, records: List[VectorRecord]):
        for record in records:
            self.records[record.id] = record
            self.index.insert(record.id, record.vector)

    def search(self, query_vector: List[float], top_k: int = 10,
               filter_metadata: Optional[Dict[str, Any]] = None,
               threshold: float = 0.0) -> List[SearchResult]:
        results = self.index.search(query_vector, k=top_k * 2)
        scored: List[SearchResult] = []
        for id, dist in results:
            record = self.records.get(id)
            if record is None:
                continue
            if filter_metadata:
                if not all(record.metadata.get(k) == v for k, v in filter_metadata.items()):
                    continue
            similarity = 1.0 / (1.0 + dist)
            if similarity >= threshold:
                scored.append(SearchResult(record=record, score=similarity))
        scored.sort(key=lambda r: r.score, reverse=True)
        for i, r in enumerate(scored[:top_k]):
            r.rank = i + 1
        return scored[:top_k]

    def delete(self, id: str):
        self.records.pop(id, None)

    def count(self) -> int:
        return len(self.records)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "dimension": self.dim,
            "count": len(self.records),
            "index_levels": len(self.index.graphs),
        }
