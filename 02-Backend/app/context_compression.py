import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.config import settings
from app.intelligence.execution_tracer import ExecutionTracer

logger = logging.getLogger(__name__)


class CompressionStrategy(str, Enum):
    EXTRACTIVE = "extractive"
    ABSTRACTIVE = "abstractive"
    HYBRID = "hybrid"
    TOKEN_TRUNCATION = "token_truncation"


@dataclass
class CompressionResult:
    compressed: str
    original_tokens: int
    compressed_tokens: int
    strategy: CompressionStrategy
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextCompressor:
    def __init__(
        self,
        compression_model: Optional[str] = None,
        tracer: Optional[ExecutionTracer] = None,
    ):
        self._client = None
        self.compression_model = compression_model or os.getenv("COMPRESSION_MODEL", "gpt-4o-mini-2024-07-18")
        self.tracer = tracer

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def compress(
        self,
        context: str,
        max_tokens: int,
        query: Optional[str] = None,
        strategy: CompressionStrategy = CompressionStrategy.HYBRID,
    ) -> CompressionResult:
        original_tokens = self.estimate_tokens(context)
        if original_tokens <= max_tokens:
            return CompressionResult(
                compressed=context,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                strategy=CompressionStrategy.TOKEN_TRUNCATION,
                metadata={"skipped": True},
            )

        if strategy == CompressionStrategy.TOKEN_TRUNCATION:
            result = self._token_truncate(context, max_tokens)
        elif strategy == CompressionStrategy.EXTRACTIVE:
            result = self._extractive_compress(context, max_tokens, query or "")
        elif strategy == CompressionStrategy.ABSTRACTIVE:
            result = self._abstractive_compress(context, max_tokens)
        else:
            result = self._hybrid_compress(context, max_tokens, query or "")

        compressed_tokens = self.estimate_tokens(result.compressed)
        if self.tracer:
            try:
                request_id = getattr(self.tracer, "_last_request_id", None)
            except Exception:
                request_id = None
            if request_id:
                self.tracer.trace_context_compression(
                    request_id=request_id,
                    original_tokens=original_tokens,
                    compressed_tokens=compressed_tokens,
                    strategy=strategy.value,
                )
        return CompressionResult(
            compressed=result.compressed,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            strategy=strategy,
            metadata=result.metadata,
        )

    def extract_important(self, context: str, query: str) -> str:
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.compression_model,
                messages=[
                    {"role": "system", "content": "Extract only the sentences most relevant to the query. Return them verbatim separated by newlines."},
                    {"role": "user", "content": f"Query: {query}\n\nContext:\n{context}"},
                ],
                max_tokens=512,
                temperature=0.0,
            )
            return response.choices[0].message.content or context
        except Exception as exc:
            logger.error(f"LLM extraction failed: {exc}")
            return self._heuristic_extract(context, query)

    def estimate_tokens(self, text: str) -> int:
        try:
            import tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def _token_truncate(self, context: str, max_tokens: int) -> CompressionResult:
        ratio = max_tokens / max(self.estimate_tokens(context), 1)
        keep = max(1, int(len(context) * ratio))
        return CompressionResult(
            compressed=context[:keep],
            original_tokens=self.estimate_tokens(context),
            compressed_tokens=self.estimate_tokens(context[:keep]),
            strategy=CompressionStrategy.TOKEN_TRUNCATION,
            metadata={"truncated": True},
        )

    def _extractive_compress(self, context: str, max_tokens: int, query: str) -> CompressionResult:
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.compression_model,
                messages=[
                    {"role": "system", "content": f"Extract only the sentences most relevant to the query. Keep under {max_tokens} tokens. Return them verbatim separated by newlines."},
                    {"role": "user", "content": f"Query: {query}\n\nContext:\n{context}"},
                ],
                max_tokens=max_tokens,
                temperature=0.0,
            )
            compressed = response.choices[0].message.content or context
            return CompressionResult(
                compressed=compressed,
                original_tokens=self.estimate_tokens(context),
                compressed_tokens=self.estimate_tokens(compressed),
                strategy=CompressionStrategy.EXTRACTIVE,
            )
        except Exception as exc:
            logger.error(f"LLM extractive compression failed: {exc}")
            heuristic = self._heuristic_extract(context, query)
            return CompressionResult(
                compressed=heuristic,
                original_tokens=self.estimate_tokens(context),
                compressed_tokens=self.estimate_tokens(heuristic),
                strategy=CompressionStrategy.EXTRACTIVE,
                metadata={"fallback": "heuristic"},
            )

    def _abstractive_compress(self, context: str, max_tokens: int) -> CompressionResult:
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.compression_model,
                messages=[
                    {"role": "system", "content": f"Compress the following context to under {max_tokens} tokens while preserving key facts. Return only the compressed text."},
                    {"role": "user", "content": context},
                ],
                max_tokens=max_tokens,
                temperature=0.0,
            )
            compressed = response.choices[0].message.content or context
            return CompressionResult(
                compressed=compressed,
                original_tokens=self.estimate_tokens(context),
                compressed_tokens=self.estimate_tokens(compressed),
                strategy=CompressionStrategy.ABSTRACTIVE,
            )
        except Exception as exc:
            logger.error(f"LLM abstractive compression failed: {exc}")
            fallback = self._heuristic_compress(context, max_tokens)
            return CompressionResult(
                compressed=fallback,
                original_tokens=self.estimate_tokens(context),
                compressed_tokens=self.estimate_tokens(fallback),
                strategy=CompressionStrategy.ABSTRACTIVE,
                metadata={"fallback": "heuristic"},
            )

    def _hybrid_compress(self, context: str, max_tokens: int, query: str) -> CompressionResult:
        extractive = self._extractive_compress(context, max_tokens, query)
        if extractive.compressed_tokens <= max_tokens:
            return extractive
        abstractive = self._abstractive_compress(context, max_tokens)
        return abstractive

    def _heuristic_extract(self, context: str, query: str) -> str:
        terms = set(query.lower().split())
        sentences = re.split(r'(?<=[.!?])\s+', context)
        scored = []
        for sentence in sentences:
            score = sum(1 for t in terms if t in sentence.lower())
            scored.append((score, sentence))
        scored.sort(key=lambda x: x[0], reverse=True)
        return " ".join(s for _, s in scored[:10])

    def _heuristic_compress(self, context: str, max_tokens: int) -> str:
        tokens_estimate = self.estimate_tokens(context)
        ratio = max_tokens / max(tokens_estimate, 1)
        keep = max(1, int(len(context) * ratio))
        return context[:keep]
