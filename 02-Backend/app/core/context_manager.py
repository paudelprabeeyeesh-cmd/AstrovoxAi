"""
Context manager for long-context windows, sliding window, and compression.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ContextChunk:
    text: str
    token_count: int
    importance: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ContextCompressor:
    """Compress long contexts while preserving key facts."""

    def __init__(self, target_ratio: float = 0.6):
        self.target_ratio = target_ratio

    def compress(self, chunks: List[ContextChunk], max_tokens: int) -> List[ContextChunk]:
        if not chunks:
            return []
        total_tokens = sum(c.token_count for c in chunks)
        if total_tokens <= max_tokens:
            return chunks
        target_tokens = int(max_tokens * self.target_ratio)
        scored = sorted(chunks, key=lambda c: c.importance, reverse=True)
        selected: List[ContextChunk] = []
        tokens = 0
        for chunk in scored:
            if tokens + chunk.token_count > target_tokens and selected:
                break
            selected.append(chunk)
            tokens += chunk.token_count
        selected.sort(key=lambda c: chunks.index(c))
        return selected


class LongContextManager:
    """Manage 128K+ token windows with sliding window and memory."""

    def __init__(self, max_tokens: int = 128_000, window_tokens: int = 32_000, compressor: Optional[ContextCompressor] = None):
        self.max_tokens = max_tokens
        self.window_tokens = window_tokens
        self.compressor = compressor or ContextCompressor()
        self.memory_store: Dict[str, List[ContextChunk]] = {}

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def build_context(self, session_id: str, query: str, retrieved: List[ContextChunk], conversation: List[Dict[str, str]]) -> List[ContextChunk]:
        query_tokens = self._estimate_tokens(query)
        remaining = max(self.max_tokens - query_tokens, 0)
        conv_chunks = [ContextChunk(text=f"{m['role']}: {m['content']}", token_count=self._estimate_tokens(m['content']), importance=0.4) for m in conversation]
        memory = self.memory_store.get(session_id, [])
        candidates = retrieved + memory + conv_chunks
        if not candidates:
            return []
        selected = self.compressor.compress(candidates, remaining)
        return selected

    def add_memory(self, session_id: str, chunk: ContextChunk):
        self.memory_store.setdefault(session_id, []).append(chunk)

    def get_memory(self, session_id: str) -> List[ContextChunk]:
        return list(self.memory_store.get(session_id, []))

    def clear_memory(self, session_id: str):
        self.memory_store.pop(session_id, None)
