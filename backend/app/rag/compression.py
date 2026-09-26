"""Context compression for RAG pipelines."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextCompressor:
    def __init__(self, max_tokens: int = 4096, compression_ratio: float = 0.6):
        self.max_tokens = max_tokens
        self.compression_ratio = compression_ratio

    def compress(self, context: str, query: str, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        max_tokens = max_tokens or self.max_tokens
        sentences = self._split_sentences(context)
        if not sentences:
            return {"compressed_context": context, "original_tokens": self._tokenize(context), "compressed_tokens": 0, "ratio": 1.0}
        query_tokens = set(self._tokenize(query))
        scored: List[tuple[float, str]] = []
        for sentence in sentences:
            tokens = set(self._tokenize(sentence))
            overlap = len(query_tokens & tokens)
            scored.append((overlap + 0.1, sentence))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected: List[str] = []
        current_tokens = 0
        for _, sentence in scored:
            tokens = self._tokenize(sentence)
            if current_tokens + len(tokens) > max_tokens:
                continue
            selected.append(sentence)
            current_tokens += len(tokens)
        selected.sort(key=lambda s: context.index(s))
        compressed = " ".join(selected) if selected else sentences[0]
        original_tokens = self._tokenize(context)
        compressed_tokens = self._tokenize(compressed)
        ratio = len(compressed_tokens) / max(len(original_tokens), 1)
        return {
            "compressed_context": compressed,
            "original_tokens": len(original_tokens),
            "compressed_tokens": len(compressed_tokens),
            "ratio": ratio,
        }

    def compress_with_llm(self, context: str, query: str, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        max_tokens = max_tokens or self.max_tokens
        sentences = self._split_sentences(context)
        if len(sentences) <= 3:
            return self.compress(context, query, max_tokens)
        selected = sentences[: max(1, int(len(sentences) * self.compression_ratio))]
        compressed = " ".join(selected)
        original_tokens = self._tokenize(context)
        compressed_tokens = self._tokenize(compressed)
        ratio = len(compressed_tokens) / max(len(original_tokens), 1)
        return {
            "compressed_context": compressed,
            "original_tokens": len(original_tokens),
            "compressed_tokens": len(compressed_tokens),
            "ratio": ratio,
        }

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [t for t in re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower()) if len(t) >= 2]
