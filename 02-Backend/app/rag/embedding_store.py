"""
Embedding Storage Service.

Manages storage and retrieval of embeddings for documents and memories.
Supports:
- Batch embedding storage
- Similarity search
- Metadata filtering
- Index management
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class StoredEmbedding:
    embedding_id: str
    document_id: str
    content: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EmbeddingStore:
    """
    Manages embedding storage and retrieval for RAG.
    
    Features:
    - Store embeddings with metadata
    - Similarity search (cosine)
    - Metadata filtering
    - Batch operations
    """

    def __init__(self):
        self._embeddings: Dict[str, StoredEmbedding] = {}
        self._by_document: Dict[str, List[str]] = {}
        self._lock = threading.RLock()

    def add_embedding(
        self,
        embedding_id: str,
        document_id: str,
        content: str,
        embedding: Union[List[float], np.ndarray],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StoredEmbedding:
        """Store a single embedding."""
        if isinstance(embedding, list):
            embedding = np.array(embedding, dtype=np.float32)
        entry = StoredEmbedding(
            embedding_id=embedding_id,
            document_id=document_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
        )
        with self._lock:
            self._embeddings[embedding_id] = entry
            self._by_document.setdefault(document_id, []).append(embedding_id)
        logger.debug("Stored embedding %s for document %s", embedding_id, document_id)
        return entry

    def add_embeddings(
        self,
        document_id: str,
        contents: List[str],
        embeddings: List[Union[List[float], np.ndarray]],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[StoredEmbedding]:
        """Store multiple embeddings for a document."""
        if len(contents) != len(embeddings):
            raise ValueError("Contents and embeddings length mismatch")
        if metadata_list is None:
            metadata_list = [{}] * len(contents)
        results = []
        for idx, (content, embedding, metadata) in enumerate(zip(contents, embeddings, metadata_list)):
            embedding_id = f"{document_id}_chunk_{idx}"
            chunk_metadata = {"chunk_index": idx, "total_chunks": len(contents)}
            chunk_metadata.update(metadata or {})
            result = self.add_embedding(
                embedding_id=embedding_id,
                document_id=document_id,
                content=content,
                embedding=embedding,
                metadata=chunk_metadata,
            )
            results.append(result)
        return results

    def get_embedding(self, embedding_id: str) -> Optional[StoredEmbedding]:
        """Get a single embedding by ID."""
        with self._lock:
            return self._embeddings.get(embedding_id)

    def get_by_document(self, document_id: str) -> List[StoredEmbedding]:
        """Get all embeddings for a document."""
        with self._lock:
            ids = self._by_document.get(document_id, [])
            return [self._embeddings[eid] for eid in ids if eid in self._embeddings]

    def delete_document(self, document_id: str) -> int:
        """Delete all embeddings for a document."""
        with self._lock:
            ids = self._by_document.pop(document_id, [])
            count = 0
            for eid in ids:
                if self._embeddings.pop(eid, None) is not None:
                    count += 1
            return count

    def _cosine_similarity(self, query: np.ndarray, candidate: np.ndarray) -> float:
        """Compute cosine similarity."""
        q_norm = np.linalg.norm(query)
        c_norm = np.linalg.norm(candidate)
        if q_norm == 0.0 or c_norm == 0.0:
            return 0.0
        return float(np.dot(query, candidate) / (q_norm * c_norm))

    def similarity_search(
        self,
        query_embedding: Union[List[float], np.ndarray],
        top_k: int = 10,
        document_ids: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[StoredEmbedding, float]]:
        """Search for similar embeddings."""
        if isinstance(query_embedding, list):
            query_embedding = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(query_embedding)
        if q_norm == 0.0:
            return []
        query_normalized = query_embedding / q_norm
        candidates = []
        with self._lock:
            for entry in self._embeddings.values():
                if document_ids and entry.document_id not in document_ids:
                    continue
                if metadata_filter:
                    match = all(entry.metadata.get(k) == v for k, v in metadata_filter.items())
                    if not match:
                        continue
                e_norm = np.linalg.norm(entry.embedding)
                if e_norm == 0.0:
                    continue
                sim = float(np.dot(query_normalized, entry.embedding / e_norm))
                candidates.append((entry, sim))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """Get embedding store statistics."""
        with self._lock:
            return {
                "total_embeddings": len(self._embeddings),
                "total_documents": len(self._by_document),
            }

    def clear(self) -> None:
        """Clear all embeddings."""
        with self._lock:
            self._embeddings.clear()
            self._by_document.clear()
