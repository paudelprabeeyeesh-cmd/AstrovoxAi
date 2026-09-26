"""Long-context optimization for RAG pipelines."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContextWindow:
    max_tokens: int = 8192
    reserved_tokens: int = 1024
    overlap_tokens: int = 128

    @property
    def available_tokens(self) -> int:
        return max(0, self.max_tokens - self.reserved_tokens)


class LongContextOptimizer:
    """Optimize long-context retrieval with sliding windows, compression, and hierarchical summarization."""

    def __init__(self, window_size: int = 4096, overlap: int = 256):
        self.window_size = window_size
        self.overlap = overlap
        self.context_window = ContextWindow(max_tokens=window_size * 2)

    def optimize(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_chars = sum(len(doc.get("content", "")) for doc in documents)
        if total_chars <= self.window_size * 4:
            return self._compact_context(query, documents)
        return self._hierarchical_context(query, documents)

    def _compact_context(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        query_terms = set(query.lower().split())
        scored = []
        for doc in documents:
            text = doc.get("content", "")
            terms = set(text.lower().split())
            overlap = len(query_terms & terms)
            scored.append((overlap, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [doc for _, doc in scored if doc.get("content", "")]
        return {
            "strategy": "compact",
            "documents": selected,
            "total_tokens": sum(len(d.get("content", "").split()) for d in selected),
        }

    def _hierarchical_context(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        chunks = []
        for doc in documents:
            text = doc.get("content", "")
            start = 0
            idx = 0
            while start < len(text):
                end = min(start + self.window_size, len(text))
                chunk_text = text[start:end]
                chunks.append({**doc, "content": chunk_text, "chunk_index": idx})
                start += self.window_size - self.overlap
                idx += 1
        return self._compact_context(query, chunks)

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def fit_to_window(self, query: str, context: str) -> str:
        available = self.context_window.available_tokens
        words = context.split()
        if len(words) <= available:
            return context
        return " ".join(words[:available])
