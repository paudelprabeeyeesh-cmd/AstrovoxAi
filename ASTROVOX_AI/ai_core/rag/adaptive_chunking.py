"""Adaptive chunking strategies for RAG pipelines."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AdaptiveChunk:
    id: str
    document_id: str
    content: str
    chunk_index: int
    char_start: int = 0
    char_end: int = 0
    token_estimate: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_type: str = "adaptive"
    complexity_score: float = 0.0


class AdaptiveChunker:
    """Adaptive chunking that adjusts chunk size based on content complexity and structure."""

    def __init__(self, min_chunk_size: int = 200, max_chunk_size: int = 1200, target_tokens: int = 512):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.target_tokens = target_tokens

    def chunk(self, text: str, document_id: str, structure_hints: Optional[List[Dict[str, Any]]] = None) -> List[AdaptiveChunk]:
        if not text or not text.strip():
            return []
        sentences = self._split_sentences(text)
        if not sentences:
            return []
        complexities = [self._complexity(s) for s in sentences]
        chunks: List[AdaptiveChunk] = []
        current: List[str] = []
        current_complexity = 0.0
        char_pos = 0
        chunk_index = 0
        for idx, sentence in enumerate(sentences):
            sentence_len = len(sentence)
            current_complexity += complexities[idx]
            projected_len = sum(len(s) for s in current) + sentence_len
            projected_complexity = current_complexity / max(len(current), 1)
            adaptive_max = self._adaptive_max(projected_complexity)
            if current and projected_len > adaptive_max:
                content = " ".join(current)
                chunks.append(AdaptiveChunk(
                    id=self._make_id(document_id, chunk_index),
                    document_id=document_id,
                    content=content,
                    chunk_index=chunk_index,
                    char_start=char_pos,
                    char_end=char_pos + len(content),
                    token_estimate=max(1, len(content.split())),
                    complexity_score=current_complexity / max(len(current), 1),
                ))
                chunk_index += 1
                char_pos += len(content) + 1
                current = []
                current_complexity = 0.0
            current.append(sentence)
        if current:
            content = " ".join(current)
            chunks.append(AdaptiveChunk(
                id=self._make_id(document_id, chunk_index),
                document_id=document_id,
                content=content,
                chunk_index=chunk_index,
                char_start=char_pos,
                char_end=char_pos + len(content),
                token_estimate=max(1, len(content.split())),
                complexity_score=current_complexity / max(len(current), 1),
            ))
        return chunks

    def _adaptive_max(self, complexity: float) -> int:
        if complexity > 0.7:
            return self.min_chunk_size
        if complexity > 0.4:
            return (self.min_chunk_size + self.max_chunk_size) // 2
        return self.max_chunk_size

    def _complexity(self, sentence: str) -> float:
        words = sentence.split()
        if not words:
            return 0.0
        avg_len = sum(len(w) for w in words) / len(words)
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        special_chars = len(re.findall(r"[^a-zA-Z0-9\s]", sentence))
        return min(1.0, (avg_len / 12.0) * 0.5 + unique_ratio * 0.3 + (special_chars / max(len(sentence), 1)) * 0.2)

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _make_id(document_id: str, index: int) -> str:
        return f"{document_id}_adaptive_chunk_{index}"
