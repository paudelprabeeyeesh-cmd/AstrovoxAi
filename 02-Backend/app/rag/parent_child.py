"""Parent-child retrieval for RAG pipelines."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParentDocument:
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class ChildChunk:
    chunk_id: str
    parent_id: str
    content: str
    chunk_index: int
    char_start: int = 0
    char_end: int = 0
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


class ParentChildStore:
    """Store parent documents and child chunks with relationship tracking."""

    def __init__(self):
        self._parents: Dict[str, ParentDocument] = {}
        self._children: Dict[str, ChildChunk] = {}
        self._child_index: Dict[str, List[str]] = {}

    def add_parent(self, parent: ParentDocument) -> None:
        self._parents[parent.doc_id] = parent
        self._child_index.setdefault(parent.doc_id, [])

    def add_child(self, child: ChildChunk) -> None:
        self._children[child.chunk_id] = child
        self._child_index.setdefault(child.parent_id, []).append(child.chunk_id)

    def get_parent(self, chunk_id: str) -> Optional[ParentDocument]:
        child = self._children.get(chunk_id)
        if not child:
            return None
        return self._parents.get(child.parent_id)

    def get_children(self, parent_id: str) -> List[ChildChunk]:
        chunk_ids = self._child_index.get(parent_id, [])
        return [self._children[cid] for cid in chunk_ids if cid in self._children]

    def get_siblings(self, chunk_id: str) -> List[ChildChunk]:
        child = self._children.get(chunk_id)
        if not child:
            return []
        return [c for c in self.get_children(child.parent_id) if c.chunk_id != chunk_id]

    @property
    def parent_count(self) -> int:
        return len(self._parents)

    @property
    def child_count(self) -> int:
        return len(self._children)


class ParentChildRetriever:
    """Retrieve child chunks and expand with parent document context."""

    def __init__(self, store: Optional[ParentChildStore] = None):
        self.store = store or ParentChildStore()

    def index(self, parent: ParentDocument, children: List[ChildChunk]) -> None:
        self.store.add_parent(parent)
        for child in children:
            self.store.add_child(child)

    def retrieve(self, query_embedding: Optional[List[float]] = None,
                 child_scores: Optional[Dict[str, float]] = None,
                 top_k: int = 5, expand_parent: bool = True) -> List[Dict[str, Any]]:
        if not child_scores:
            return []
        ranked = sorted(child_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        seen_parents = set()
        for chunk_id, score in ranked:
            child = self.store._children.get(chunk_id)
            if not child:
                continue
            parent = self.store.get_parent(chunk_id)
            result: Dict[str, Any] = {
                "chunk_id": chunk_id,
                "parent_id": child.parent_id,
                "content": child.content,
                "score": score,
                "chunk_index": child.chunk_index,
            }
            if expand_parent and parent and parent.doc_id not in seen_parents:
                result["parent_content"] = parent.content
                result["parent_metadata"] = parent.metadata
                seen_parents.add(parent.doc_id)
            results.append(result)
        return results

    def retrieve_with_siblings(self, chunk_id: str, max_siblings: int = 2) -> Dict[str, Any]:
        child = self.store._children.get(chunk_id)
        if not child:
            return {}
        siblings = self.store.get_siblings(chunk_id)[:max_siblings]
        parent = self.store.get_parent(chunk_id)
        return {
            "chunk_id": chunk_id,
            "content": child.content,
            "parent": parent.content if parent else "",
            "siblings": [s.content for s in siblings],
        }
