"""Parent-child chunk retrieval for RAG pipelines."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParentDocument:
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChildChunk:
    id: str
    parent_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


class ParentChildStore:
    def __init__(self):
        self._parents: Dict[str, ParentDocument] = {}
        self._children: Dict[str, ChildChunk] = {}
        self._children_by_parent: Dict[str, List[str]] = {}

    def add_parent(self, document: ParentDocument) -> None:
        self._parents[document.id] = document
        self._children_by_parent.setdefault(document.id, [])

    def add_child(self, chunk: ChildChunk) -> None:
        self._children[chunk.id] = chunk
        self._children_by_parent.setdefault(chunk.parent_id, []).append(chunk.id)

    def get_parent(self, parent_id: str) -> Optional[ParentDocument]:
        return self._parents.get(parent_id)

    def get_children(self, parent_id: str) -> List[ChildChunk]:
        child_ids = self._children_by_parent.get(parent_id, [])
        return [self._children[cid] for cid in child_ids if cid in self._children]

    def get_child(self, child_id: str) -> Optional[ChildChunk]:
        return self._children.get(child_id)


class ParentChildRetriever:
    def __init__(self, store: Optional[ParentChildStore] = None):
        self.store = store or ParentChildStore()

    def index(self, document: ParentDocument, child_chunks: List[ChildChunk]) -> None:
        self.store.add_parent(document)
        for chunk in child_chunks:
            self.store.add_child(chunk)

    def retrieve(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        import math
        scored: List[tuple[float, ChildChunk]] = []
        for chunk in self.store._children.values():
            if not chunk.embedding:
                continue
            dot = sum(a * b for a, b in zip(query_embedding, chunk.embedding))
            norm_q = math.sqrt(sum(v * v for v in query_embedding)) or 1.0
            norm_c = math.sqrt(sum(v * v for v in chunk.embedding)) or 1.0
            scored.append((dot / (norm_q * norm_c), chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        seen_parents = set()
        for score, chunk in scored:
            if chunk.parent_id in seen_parents:
                continue
            seen_parents.add(chunk.parent_id)
            parent = self.store.get_parent(chunk.parent_id)
            results.append({
                "chunk_id": chunk.id,
                "parent_id": chunk.parent_id,
                "score": score,
                "content": parent.content if parent else chunk.content,
                "child_content": chunk.content,
                "metadata": {**(parent.metadata if parent else {}), **chunk.metadata},
            })
            if len(results) >= top_k:
                break
        return results
