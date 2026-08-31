"""Embeddings service — provides text embedding generation via AI providers."""

import os
import asyncio
import logging
from typing import Optional

from .providers.base import EmbeddingVector

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using configured providers."""

    def __init__(self):
        self._provider = None
        self._model = "models/embedding-001"
        self._initialize_provider()

    def _initialize_provider(self):
        from .providers.factory import ProviderFactory
        gemini = ProviderFactory.get("gemini")
        if gemini and gemini.is_configured:
            self._provider = gemini
            logger.info("Embedding service initialized with Gemini provider")
        else:
            logger.warning("Gemini provider not configured. Set GEMINI_API_KEY to enable embeddings.")

    @property
    def is_configured(self) -> bool:
        return self._provider is not None

    @property
    def model(self) -> str:
        return self._model

    async def embed(self, texts: list[str], model: Optional[str] = None) -> list[EmbeddingVector]:
        if not self.is_configured:
            raise RuntimeError("No embedding provider configured. Set GEMINI_API_KEY.")
        if not texts:
            return []
        model = model or self._model
        return await self._provider.embed(texts, model=model)

    async def embed_one(self, text: str, model: Optional[str] = None) -> EmbeddingVector:
        results = await self.embed([text], model=model)
        return results[0]

    async def embed_with_retry(self, texts: list[str], model: Optional[str] = None, max_retries: int = 2) -> list[EmbeddingVector]:
        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                return await self.embed(texts, model=model)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_transient = any(kw in error_str for kw in ["timeout", "rate limit", "429", "503", "502", "504", "connection", "temporary"])
                if is_transient and attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning("Embedding request failed (attempt %d/%d), retrying in %ds: %s", attempt + 1, max_retries + 1, wait, str(e))
                    await asyncio.sleep(wait)
                    continue
                raise
        raise last_error


embedding_service = EmbeddingService()
