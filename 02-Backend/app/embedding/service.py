"""Embedding Service — High-level embedding operations with caching, retries, and fallback."""

import time
from typing import Optional

from .providers import (
    EmbeddingProvider,
    EmbeddingBatchResult,
    EmbeddingVector,
    EmbeddingConfig,
    EmbeddingProviderFactory,
    OpenAIEmbeddingProvider,
    OllamaEmbeddingProvider,
)
from .cache import EmbeddingCache


class EmbeddingService:
    """Production-grade embedding service with caching and provider fallback."""

    def __init__(
        self,
        provider_name: str = "openai",
        model: Optional[str] = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
    ):
        self.provider_name = provider_name
        self.model = model
        self.use_cache = use_cache
        self.cache = EmbeddingCache(ttl=cache_ttl) if use_cache else None
        self._provider = None

    @property
    def provider(self) -> Optional[EmbeddingProvider]:
        if self._provider is None:
            self._provider = EmbeddingProviderFactory.get(self.provider_name)
        return self._provider

    async def embed_text(self, text: str) -> EmbeddingVector:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        text = text.strip()

        # Check cache
        if self.cache and self.provider:
            cached = self.cache.get(text, self.model or self.provider.default_model, self.provider_name)
            if cached:
                return cached

        # Generate embedding
        result = await self.embed_batch([text])
        embedding = result.embeddings[0]

        # Cache result
        if self.cache:
            self.cache.set(text, embedding.model, self.provider_name, embedding)

        return embedding

    async def embed_batch(self, texts: list[str]) -> EmbeddingBatchResult:
        """Generate embeddings for multiple texts with caching and retries."""
        if not texts:
            return EmbeddingBatchResult(embeddings=[], model="", provider="", batch_size=0)

        texts = [t.strip() for t in texts if t and t.strip()]
        model = self.model or (self.provider.default_model if self.provider else "text-embedding-3-small")

        # Check cache for existing embeddings
        to_embed = texts
        cached_embeddings = []

        if self.cache and self.provider:
            cached_embeddings, to_embed = self.cache.get_many(texts, model, self.provider_name)

        # Generate missing embeddings
        if to_embed and self.provider:
            result = await self._embed_with_retry(to_embed, model)
            # Cache new results
            if self.cache:
                for text, emb in zip(to_embed, result.embeddings):
                    self.cache.set(text, emb.model, self.provider_name, emb)
            # Combine cached + new
            all_embeddings = cached_embeddings + result.embeddings
        else:
            all_embeddings = cached_embeddings

        return EmbeddingBatchResult(
            embeddings=all_embeddings,
            model=model,
            provider=self.provider_name,
            batch_size=len(all_embeddings),
        )

    async def _embed_with_retry(self, texts: list[str], model: str) -> EmbeddingBatchResult:
        """Embed with automatic retry and provider fallback."""
        max_retries = self.provider.config.max_retries if self.provider else 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return await self.provider.embed(texts)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff

        # Try fallback provider
        fallback = self._get_fallback_provider()
        if fallback:
            try:
                return await fallback.embed(texts)
            except Exception:
                pass

        sanitized = self.provider.sanitize_error(last_error) if self.provider else str(last_error)
        raise RuntimeError(f"Embedding failed after {max_retries + 1} attempts: {sanitized}")

    def _get_fallback_provider(self) -> Optional[EmbeddingProvider]:
        """Get a fallback provider when primary fails."""
        for name in ["ollama", "openai"]:
            if name != self.provider_name:
                provider = EmbeddingProviderFactory.get(name)
                if provider and provider.is_configured:
                    return provider
        return None

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            raise ValueError(f"Dimension mismatch: {len(a)} vs {len(b)}")

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    async def similarity(self, text_a: str, text_b: str) -> float:
        """Calculate semantic similarity between two texts."""
        emb_a = await self.embed_text(text_a)
        emb_b = await self.embed_text(text_b)
        return self.cosine_similarity(emb_a.vector, emb_b.vector)
