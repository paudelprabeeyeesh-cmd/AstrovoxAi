"""Context optimization for RAG pipelines."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContextOptimizer:
    """Optimize context windows for long documents and large retrievals."""

    def __init__(self, max_tokens: int = 4096, compression_ratio: float = 0.6):
        self.max_tokens = max_tokens
        self.compression_ratio = compression_ratio

    def optimize(self, context: str, query: str, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        max_tokens = max_tokens or self.max_tokens
        sentences = self._split_sentences(context)
        if not sentences:
            return {"optimized_context": context, "original_tokens": self._tokenize(context), "optimized_tokens": 0, "ratio": 1.0}
        query_tokens = set(self._tokenize(query))
        scored = []
        for sentence in sentences:
            tokens = set(self._tokenize(sentence))
            overlap = len(query_tokens & tokens)
            scored.append((overlap + 0.1, sentence))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = []
        current_tokens = 0
        for _, sentence in scored:
            tokens = self._tokenize(sentence)
            if current_tokens + len(tokens) > max_tokens:
                continue
            selected.append(sentence)
            current_tokens += len(tokens)
        selected.sort(key=lambda s: context.index(s))
        optimized = " ".join(selected) if selected else sentences[0]
        original_tokens = self._tokenize(context)
        optimized_tokens = self._tokenize(optimized)
        ratio = len(optimized_tokens) / max(len(original_tokens), 1)
        return {
            "optimized_context": optimized,
            "original_tokens": len(original_tokens),
            "optimized_tokens": len(optimized_tokens),
            "ratio": ratio,
        }

    def summarize(self, context: str, max_tokens: Optional[int] = None) -> str:
        result = self.optimize(context, "", max_tokens)
        return result.get("optimized_context", context)

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [t for t in re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower()) if len(t) >= 2]
