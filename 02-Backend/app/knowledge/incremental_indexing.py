"""
Incremental Indexing - Updates search indexes without full rebuild.

Supports:
- Append-only document additions
- Deletions and updates
- Delta embedding generation
- Index merge strategies
"""

from typing import Any, Dict, List, Optional


class IncrementalIndex:
    """Incremental index for documents and embeddings."""

    def __init__(self):
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._pending_additions: List[Dict[str, Any]] = []
        self._pending_deletions: List[str] = []
        self._version = 0

    def add_document(self, doc_id: str, content: str, embedding: Optional[List[float]] = None, metadata: Optional[Dict[str, Any]] = None):
        self._pending_additions.append({
            "doc_id": doc_id,
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "version": self._version + 1,
        })

    def delete_document(self, doc_id: str):
        self._pending_deletions.append(doc_id)

    def commit(self) -> Dict[str, Any]:
        added = 0
        for doc in self._pending_additions:
            self._documents[doc["doc_id"]] = doc
            added += 1
        for doc_id in self._pending_deletions:
            self._documents.pop(doc_id, None)
        self._version += 1
        additions = len(self._pending_additions)
        deletions = len(self._pending_deletions)
        self._pending_additions.clear()
        self._pending_deletions.clear()
        return {
            "version": self._version,
            "added": additions,
            "deleted": deletions,
            "total": len(self._documents),
        }

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self._documents.get(doc_id)

    def list_documents(self) -> List[Dict[str, Any]]:
        return list(self._documents.values())

    def search(self, query_embedding: Optional[List[float]], top_k: int = 10) -> List[Dict[str, Any]]:
        if not query_embedding:
            return []
        import math
        q_norm = math.sqrt(sum(x * x for x in query_embedding))
        if q_norm == 0:
            return []
        scored = []
        for doc in self._documents.values():
            emb = doc.get("embedding")
            if not emb:
                continue
            norm = math.sqrt(sum(x * x for x in emb))
            if norm == 0:
                continue
            score = sum(x * y for x, y in zip(query_embedding, emb)) / (q_norm * norm)
            scored.append({**doc, "score": score})
        scored.sort(key=lambda d: d.get("score", 0.0), reverse=True)
        return scored[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "version": self._version,
            "total_documents": len(self._documents),
            "pending_additions": len(self._pending_additions),
            "pending_deletions": len(self._pending_deletions),
        }
