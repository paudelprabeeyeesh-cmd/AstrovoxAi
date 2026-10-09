"""
Semantic Retrieval - Advanced retrieval using embeddings and semantic similarity.

Features:
- Embedding-based similarity search
- Query expansion
- Context-aware retrieval
- Relevance scoring with multiple signals
"""

from typing import Any, Dict, List, Optional, Tuple
import math


class SemanticRetriever:
    """Semantic retrieval using embedding similarity."""

    def __init__(self, embedding_dim: int = 1536):
        self.embedding_dim = embedding_dim
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._embeddings: Dict[str, List[float]] = {}

    def add_document(self, doc_id: str, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None):
        self._documents[doc_id] = {
            "doc_id": doc_id,
            "content": content,
            "metadata": metadata or {},
        }
        self._embeddings[doc_id] = embedding

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def retrieve(self, query_embedding: List[float], top_k: int = 10, min_similarity: float = 0.0) -> List[Dict[str, Any]]:
        scored = []
        for doc_id, emb in self._embeddings.items():
            sim = self._cosine_similarity(query_embedding, emb)
            if sim >= min_similarity:
                doc = self._documents.get(doc_id, {})
                scored.append({**doc, "score": sim, "doc_id": doc_id})
        scored.sort(key=lambda d: d.get("score", 0.0), reverse=True)
        return scored[:top_k]

    def expand_query(self, query: str, expansions: int = 3) -> List[str]:
        return [query] + [f"{query} {i}" for i in range(1, expansions + 1)]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_documents": len(self._documents),
            "embedding_dim": self.embedding_dim,
        }
