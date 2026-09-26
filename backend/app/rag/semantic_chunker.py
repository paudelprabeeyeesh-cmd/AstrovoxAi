"""Semantic chunking strategies for RAG pipelines using sentence embeddings."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SemanticChunk:
    id: str
    document_id: str
    content: str
    chunk_index: int
    char_start: int = 0
    char_end: int = 0
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    similarity_score: float = 0.0


class SemanticChunker:
    """Semantic chunking using embedding similarity to detect topic boundaries."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, similarity_threshold: float = 0.5):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.similarity_threshold = similarity_threshold

    def chunk(self, text: str, document_id: str, embeddings: Optional[List[List[float]]] = None) -> List[SemanticChunk]:
        if not text or not text.strip():
            return []
        sentences = self._split_sentences(text)
        if not sentences:
            return []
        if embeddings and len(embeddings) == len(sentences):
            return self._chunk_by_similarity(sentences, embeddings, document_id)
        return self._chunk_by_sliding_with_semantic(sentences, document_id)

    def _chunk_by_similarity(self, sentences: List[str], embeddings: List[List[float]], document_id: str) -> List[SemanticChunk]:
        chunks: List[SemanticChunk] = []
        current: List[str] = []
        current_embs: List[List[float]] = []
        char_pos = 0
        chunk_index = 0
        for idx, (sentence, emb) in enumerate(zip(sentences, embeddings)):
            if len(current) >= self.chunk_size // 20:
                if current_embs and len(current_embs) > 1:
                    sim = self._avg_cosine(current_embs[-1], current_embs[0])
                    if sim < self.similarity_threshold:
                        content = " ".join(current)
                        chunks.append(SemanticChunk(
                            id=self._make_id(document_id, chunk_index),
                            document_id=document_id,
                            content=content,
                            chunk_index=chunk_index,
                            char_start=char_pos,
                            char_end=char_pos + len(content),
                            token_estimate=max(1, len(content.split())),
                            similarity_score=sim,
                        ))
                        chunk_index += 1
                        char_pos += len(content) + 1
                        current = []
                        current_embs = []
                        continue
            current.append(sentence)
            current_embs.append(emb)
        if current:
            content = " ".join(current)
            sim = self._avg_cosine(current_embs[-1], current_embs[0]) if len(current_embs) > 1 else 1.0
            chunks.append(SemanticChunk(
                id=self._make_id(document_id, chunk_index),
                document_id=document_id,
                content=content,
                chunk_index=chunk_index,
                char_start=char_pos,
                char_end=char_pos + len(content),
                token_estimate=max(1, len(content.split())),
                similarity_score=sim,
            ))
        return chunks or [SemanticChunk(id=self._make_id(document_id, 0), document_id=document_id, content=" ".join(sentences), chunk_index=0, token_estimate=max(1, len(" ".join(sentences).split())))]

    def _chunk_by_sliding_with_semantic(self, sentences: List[str], document_id: str) -> List[SemanticChunk]:
        chunks: List[SemanticChunk] = []
        step = max(1, self.chunk_size // 20)
        char_pos = 0
        chunk_index = 0
        for i in range(0, len(sentences), step):
            content = " ".join(sentences[i:i + step])
            if content.strip():
                chunks.append(SemanticChunk(
                    id=self._make_id(document_id, chunk_index),
                    document_id=document_id,
                    content=content,
                    chunk_index=chunk_index,
                    char_start=char_pos,
                    char_end=char_pos + len(content),
                    token_estimate=max(1, len(content.split())),
                    similarity_score=1.0,
                ))
                char_pos += len(content) + 1
                chunk_index += 1
        return chunks

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        import re
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _avg_cosine(a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 1.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _make_id(document_id: str, index: int) -> str:
        return f"{document_id}_chunk_{index}"
