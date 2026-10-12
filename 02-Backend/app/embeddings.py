"""Embeddings service — provides text embedding generation via AI providers.

Currently supports Google Gemini Embedding API with batch processing,
retry handling, and timeout support.
"""

import asyncio
import logging
from typing import Optional

from app.providers.base import EmbeddingVector
from app import embedding_spend

logger = logging.getLogger(__name__)

# A batch above this is refused before any spend; Gemini's own limit is 100,
# so a larger request would fail anyway, and the cap makes that failure a
# deliberate one rather than a provider rejection after billing.
MAX_BATCH = 100


def authorize(
    user_id: Optional[str],
    tenant_id: Optional[str],
    model: str,
    texts: list[str],
) -> None:
    """Refuse a batch that would breach the user's daily spend."""
    embedding_spend.authorize(
        embedding_spend.get_spend_cap(), user_id, tenant_id, model, texts
    )


def record(
    user_id: Optional[str],
    tenant_id: Optional[str],
    model: str,
    texts: list[str],
) -> None:
    """Record the tokens consumed. Never raises."""
    embedding_spend.record(
        embedding_spend.get_spend_cap(), user_id, tenant_id, model, texts
    )


class EmbeddingService:
    """Service for generating text embeddings using configured providers."""

    def __init__(self):
        self._provider = None
        self._model = "models/embedding-001"
        self._initialize_provider()

    def _initialize_provider(self):
        """Initialize the embedding provider from environment variables."""
        from app.providers.factory import ProviderFactory

        gemini = ProviderFactory.get("gemini")
        if gemini and gemini.is_configured:
            self._provider = gemini
            logger.info("Embedding service initialized with Gemini provider")
        else:
            logger.warning(
                "Gemini provider not configured. "
                "Set GEMINI_API_KEY to enable embeddings."
            )

    @property
    def is_configured(self) -> bool:
        """Check if an embedding provider is available."""
        return self._provider is not None

    @property
    def model(self) -> str:
        """Get the current embedding model name."""
        return self._model

    async def embed(
        self,
        texts: list[str],
        model: Optional[str] = None,
        *,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> list[EmbeddingVector]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.
            model: Optional model override.

        Returns:
            List of EmbeddingVector objects.

        Raises:
            RuntimeError: If no embedding provider is configured.
        """
        if not self.is_configured:
            raise RuntimeError(
                "No embedding provider configured. Set GEMINI_API_KEY."
            )

        if not texts:
            return []

        # The spend cap in app/ai_spend_cap.py covers chat only. This path is
        # billed per input token, so an account that stops using chat and
        # starts using search is otherwise unbounded.
        if len(texts) > MAX_BATCH:
            raise ValueError(
                f"A batch of {len(texts)} texts exceeds the limit of "
                f"{MAX_BATCH}; split the request."
            )
        authorize(user_id, tenant_id, model or self._model, texts)
        model = model or self._model
        result = await self._provider.embed(texts, model=model)
        # Meter after the call. A metering failure must not break the
        # request, so record() swallows its own errors.
        record(user_id, tenant_id, model, texts)
        return result

    async def embed_one(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> EmbeddingVector:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed.
            model: Optional model override.

        Returns:
            EmbeddingVector object.
        """
        results = await self.embed([text], model=model)
        return results[0]

    async def embed_with_retry(
        self,
        texts: list[str],
        model: Optional[str] = None,
        max_retries: int = 2,
    ) -> list[EmbeddingVector]:
        """Generate embeddings with automatic retry on failure.

        Args:
            texts: List of text strings to embed.
            model: Optional model override.
            max_retries: Maximum number of retry attempts.

        Returns:
            List of EmbeddingVector objects.
        """
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                return await self.embed(texts, model=model)
            except Exception as _e:  # noqa: BLE001
                last_error = _e
                error_str = str(_e).lower()
                is_transient = any(
                    kw in error_str
                    for kw in [
                        "timeout",
                        "rate limit",
                        "429",
                        "503",
                        "502",
                        "504",
                        "connection",
                        "temporary",
                    ]
                )
                if is_transient and attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning(
                        "Embedding request failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        max_retries + 1,
                        wait,
                        str(_e),
                    )
                    await asyncio.sleep(wait)
                    continue
                raise

        raise last_error


# Singleton instance
embedding_service = EmbeddingService()

