"""Context compression for RAG pipelines."""

from __future__ import annotations

import logging
import os
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


class ContextCompressor:
    """Compress retrieved context while preserving key information."""

    def __init__(self, max_tokens: int = 4096, use_llm: bool = True):
        self.max_tokens = max_tokens
        self.use_llm = use_llm

    def compress(self, context: str, query: str, max_tokens: Optional[int] = None) -> str:
        max_tokens = max_tokens or self.max_tokens
        estimated = self.estimate_tokens(context)
        if estimated <= max_tokens:
            return context
        if self.use_llm:
            return self._llm_compress(context, query, max_tokens)
        return self._heuristic_compress(context, query, max_tokens)

    def compress_chunks(self, chunks: List[str], query: str, max_tokens: Optional[int] = None) -> List[str]:
        max_tokens = max_tokens or self.max_tokens
        total = sum(self.estimate_tokens(c) for c in chunks)
        if total <= max_tokens:
            return chunks
        budget = max_tokens // len(chunks) if chunks else max_tokens
        return [self.compress(c, query, max_tokens=budget) for c in chunks]

    def extract_important(self, context: str, query: str, max_sentences: int = 10) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", context)
        query_terms = set(query.lower().split())
        scored = []
        for sentence in sentences:
            score = sum(1 for t in query_terms if t in sentence.lower())
            scored.append((score, sentence))
        scored.sort(key=lambda x: x[0], reverse=True)
        return " ".join(s for _, s in scored[:max_sentences])

    def estimate_tokens(self, text: str) -> int:
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def _llm_compress(self, context: str, query: str, max_tokens: int) -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
            response = client.chat.completions.create(
                model=os.getenv("COMPRESSION_MODEL", "gpt-4o-mini-2024-07-18"),
                messages=[
                    {"role": "system", "content": f"Compress the following context to under {max_tokens} tokens while preserving key facts relevant to the query. Return only the compressed text."},
                    {"role": "user", "content": f"Query: {query}\n\nContext:\n{context}"},
                ],
                max_tokens=max_tokens,
                temperature=0.0,
            )
            return response.choices[0].message.content or context
        except Exception as exc:
            logger.warning("LLM compression failed: %s", exc)
            return self._heuristic_compress(context, query, max_tokens)

    def _heuristic_compress(self, context: str, query: str, max_tokens: int) -> str:
        tokens_estimate = self.estimate_tokens(context)
        ratio = max_tokens / max(tokens_estimate, 1)
        keep = max(1, int(len(context) * ratio))
        return context[:keep]
