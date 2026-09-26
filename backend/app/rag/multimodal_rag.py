"""Multi-modal RAG for text, image, and audio retrieval."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class MultiModalChunk:
    chunk_id: str
    document_id: str
    text_content: str = ""
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiModalRAG:
    """Multi-modal RAG supporting text, image, and audio retrieval."""

    def __init__(self, text_weight: float = 0.7, image_weight: float = 0.2, audio_weight: float = 0.1):
        self.text_weight = text_weight
        self.image_weight = image_weight
        self.audio_weight = audio_weight
        self.chunks: Dict[str, MultiModalChunk] = {}

    def index(self, chunk: MultiModalChunk) -> None:
        self.chunks[chunk.chunk_id] = chunk

    def index_batch(self, chunks: List[MultiModalChunk]) -> None:
        for chunk in chunks:
            self.index(chunk)

    def retrieve(self, query: str, query_embedding: Optional[List[float]] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        scored = []
        query_terms = set(query.lower().split())
        for chunk_id, chunk in self.chunks.items():
            score = self._score(chunk, query_terms, query_embedding)
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "content": c.text_content,
                "image_path": c.image_path,
                "audio_path": c.audio_path,
                "score": score,
                "metadata": c.metadata,
            }
            for score, c in scored[:top_k]
        ]

    def _score(self, chunk: MultiModalChunk, query_terms: set, query_embedding: Optional[List[float]]) -> float:
        text_score = 0.0
        if chunk.text_content:
            text_terms = set(chunk.text_content.lower().split())
            text_score = len(query_terms & text_terms) / max(len(query_terms), 1)
        embedding_score = 0.0
        if query_embedding and chunk.embedding:
            embedding_score = sum(a * b for a, b in zip(query_embedding, chunk.embedding))
        return self.text_weight * text_score + (1.0 - self.text_weight) * embedding_score

    def remove(self, chunk_id: str) -> bool:
        return self.chunks.pop(chunk_id, None) is not None

    def count(self) -> int:
        return len(self.chunks)
