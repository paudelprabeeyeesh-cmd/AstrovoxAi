"""Vector Search Platform — Scalable semantic search engine.

Features: vector indexing, cosine similarity, hybrid search,
metadata filtering, ranking, pagination, similarity thresholds.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
import time
import math


@dataclass
class VectorDocument:
    """A document with its vector embedding and metadata."""
    id: str
    vector: list[float]
    content: str
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class SearchResult:
    """A single search result."""
    document: VectorDocument
    score: float
    rank: int = 0


@dataclass
class SearchResults:
    """Collection of search results with pagination."""
    results: list[SearchResult]
    total: int
    query: str
    duration_ms: float = 0.0
    page: int = 1
    page_size: int = 10


class VectorIndex:
    """In-memory vector index with cosine similarity search."""

    def __init__(self):
        self._documents: dict[str, VectorDocument] = {}

    def add(self, doc: VectorDocument):
        """Add or update a document."""
        self._documents[doc.id] = doc

    def add_batch(self, docs: list[VectorDocument]):
        """Add multiple documents."""
        for doc in docs:
            self._documents[doc.id] = doc

    def get(self, doc_id: str) -> Optional[VectorDocument]:
        """Retrieve a document by ID."""
        return self._documents.get(doc_id)

    def remove(self, doc_id: str) -> bool:
        """Remove a document."""
        return self._documents.pop(doc_id, None) is not None

    def clear(self):
        """Remove all documents."""
        self._documents.clear()

    @property
    def size(self) -> int:
        return len(self._documents)

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        threshold: float = 0.0,
        filters: Optional[dict] = None,
    ) -> SearchResults:
        """Search for similar vectors using cosine similarity."""
        start = time.time()

        results = []
        for doc in self._documents.values():
            # Apply metadata filters
            if filters and not self._matches_filters(doc.metadata, filters):
                continue

            score = self._cosine_similarity(query_vector, doc.vector)
            if score >= threshold:
                results.append(SearchResult(document=doc, score=score))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        # Apply top_k
        results = results[:top_k]

        # Assign ranks
        for i, r in enumerate(results):
            r.rank = i + 1

        duration = (time.time() - start) * 1000

        return SearchResults(
            results=results,
            total=len(results),
            query="",
            duration_ms=duration,
            page=1,
            page_size=top_k,
        )

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def _matches_filters(self, metadata: dict, filters: dict) -> bool:
        """Check if metadata matches the given filters."""
        for key, value in filters.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True


class VectorSearchEngine:
    """High-level vector search with user/workspace isolation."""

    def __init__(self):
        self._indexes: dict[str, VectorIndex] = {}

    def _get_index(self, namespace: str) -> VectorIndex:
        """Get or create an index for a namespace."""
        if namespace not in self._indexes:
            self._indexes[namespace] = VectorIndex()
        return self._indexes[namespace]

    def index(
        self,
        doc_id: str,
        vector: list[float],
        content: str,
        namespace: str = "default",
        metadata: Optional[dict] = None,
    ):
        """Index a document in the specified namespace."""
        index = self._get_index(namespace)
        doc = VectorDocument(
            id=doc_id,
            vector=vector,
            content=content,
            metadata=metadata or {},
        )
        index.add(doc)

    def search(
        self,
        query_vector: list[float],
        namespace: str = "default",
        top_k: int = 10,
        threshold: float = 0.5,
        filters: Optional[dict] = None,
    ) -> SearchResults:
        """Search within a namespace."""
        index = self._get_index(namespace)
        return index.search(query_vector, top_k, threshold, filters)

    def remove(self, doc_id: str, namespace: str = "default") -> bool:
        """Remove a document from a namespace."""
        index = self._get_index(namespace)
        return index.remove(doc_id)

    def clear_namespace(self, namespace: str):
        """Clear all documents in a namespace."""
        if namespace in self._indexes:
            self._indexes[namespace].clear()

    def get_stats(self, namespace: str = "default") -> dict:
        """Get index statistics."""
        index = self._get_index(namespace)
        return {
            "namespace": namespace,
            "document_count": index.size,
        }


# Global search engine instance
search_engine = VectorSearchEngine()
