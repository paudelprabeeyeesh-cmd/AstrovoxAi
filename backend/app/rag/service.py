"""RAG service with document ingestion, chunking, and retrieval."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .embeddings import EmbeddingGenerator
from .retrieval import HybridRetriever, RetrievalResult

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self) -> None:
        self._embedding_generator = EmbeddingGenerator()
        self._retriever = HybridRetriever()
        self._documents: dict[str, dict] = {}

    def ingest_document(self, user_id: str, title: str, content: str, metadata: dict | None = None) -> dict:
        chunks = self._chunk_text(content)
        embedding_results = self._embedding_generator.embed_batch(chunks)
        embeddings = [er.embedding for er in embedding_results]
        doc_id = f"doc-{len(self._documents) + 1}"
        document = {
            "id": doc_id,
            "user_id": user_id,
            "title": title,
            "content": content,
            "chunks": chunks,
            "embeddings": embeddings,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        }
        self._documents[doc_id] = document
        for i, chunk in enumerate(chunks):
            self._retriever.index(f"{doc_id}:{i}", chunk, embeddings[i])
        logger.info("Ingested document %s with %d chunks", doc_id, len(chunks))
        return document

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        if not text or not text.strip():
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            remaining = len(text) - start
            if remaining < overlap and chunks:
                break
            chunk = text[start:min(end, len(text))]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap
            if start >= len(text):
                break
        return chunks

    def search(self, query: str, user_id: str, limit: int = 5, min_similarity: float = 0.7) -> list[dict]:
        query_embedding = self._embedding_generator.embed(query).embedding
        results = []
        for doc in self._documents.values():
            if doc["user_id"] != user_id:
                continue
            for i, chunk_embedding in enumerate(doc["embeddings"]):
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                if similarity >= min_similarity:
                    results.append({
                        "document_id": doc["id"],
                        "document_title": doc["title"],
                        "chunk": doc["chunks"][i],
                        "similarity": similarity,
                        "metadata": doc["metadata"],
                    })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def get_document(self, doc_id: str) -> dict | None:
        return self._documents.get(doc_id)

    def list_documents(self, user_id: str) -> list[dict]:
        return [d for d in self._documents.values() if d["user_id"] == user_id]

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self._documents:
            del self._documents[doc_id]
            return True
        return False
