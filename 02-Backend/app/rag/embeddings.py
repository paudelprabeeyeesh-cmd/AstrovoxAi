"""Embedding generation for RAG pipelines."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    text: str
    embedding: List[float]
    model: str = "text-embedding-3-small"
    dimensions: int = 1536


class EmbeddingGenerator:
    """Generate embeddings for text chunks using configurable providers."""

    def __init__(self, model: str = "text-embedding-3-small", dimensions: int = 1536):
        self.model = model
        self.dimensions = dimensions
        self._cache: Dict[str, List[float]] = {}

    def embed(self, text: str) -> EmbeddingResult:
        if not text:
            return EmbeddingResult(text=text, embedding=[0.0] * self.dimensions, model=self.model)
        cache_key = f"{self.model}:{hash(text)}"
        if cache_key in self._cache:
            return EmbeddingResult(text=text, embedding=self._cache[cache_key], model=self.model)
        embedding = self._call_provider(text)
        self._cache[cache_key] = embedding
        return EmbeddingResult(text=text, embedding=embedding, model=self.model, dimensions=len(embedding))

    def embed_batch(self, texts: List[str], batch_size: int = 64) -> List[EmbeddingResult]:
        results: List[EmbeddingResult] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                results.append(self.embed(text))
        return results

    def _call_provider(self, text: str) -> List[float]:
        provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
        if provider == "openai":
            return self._openai_embed(text)
        if provider == "ollama":
            return self._ollama_embed(text)
        return self._heuristic_embed(text)

    def _openai_embed(self, text: str) -> List[float]:
        try:
            import openai
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
            response = client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding
        except Exception as exc:
            logger.warning("OpenAI embedding failed: %s", exc)
            return self._heuristic_embed(text)

    def _ollama_embed(self, text: str) -> List[float]:
        try:
            import requests
            base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            response = requests.post(
                f"{base}/api/embeddings",
                json={"model": os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"), "prompt": text},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
        except Exception as exc:
            logger.warning("Ollama embedding failed: %s", exc)
            return self._heuristic_embed(text)

    def _heuristic_embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dimensions
        words = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
        for i, word in enumerate(words[: self.dimensions]):
            vec[i % self.dimensions] += hash(word) % 100 / 100.0
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def clear_cache(self):
        self._cache.clear()
