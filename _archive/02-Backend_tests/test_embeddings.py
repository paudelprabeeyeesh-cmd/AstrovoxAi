"""Tests for the embeddings service and routes."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.providers.base import EmbeddingVector, ProviderConfig


# ============================================================================
# EmbeddingVector Tests
# ============================================================================

class TestEmbeddingVector:
    def test_creation(self):
        vec = EmbeddingVector(vector=[0.1, 0.2, 0.3], model="embedding-001")
        assert vec.vector == [0.1, 0.2, 0.3]
        assert vec.model == "embedding-001"
        assert vec.tokens_used is None

    def test_with_tokens(self):
        vec = EmbeddingVector(vector=[0.5], model="m", tokens_used=10)
        assert vec.tokens_used == 10


# ============================================================================
# EmbeddingService Tests
# ============================================================================

class TestEmbeddingService:
    def test_init_without_provider(self):
        from app.embeddings import EmbeddingService
        with patch("app.providers.factory.ProviderFactory") as mock_factory:
            mock_factory.get.return_value = None
            service = EmbeddingService()
            assert service.is_configured is False

    def test_init_with_provider(self):
        from app.embeddings import EmbeddingService
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        with patch("app.providers.factory.ProviderFactory") as mock_factory:
            mock_factory.get.return_value = mock_provider
            service = EmbeddingService()
            assert service.is_configured is True

    @pytest.mark.asyncio
    async def test_embed_without_provider_raises(self):
        from app.embeddings import EmbeddingService
        with patch("app.providers.factory.ProviderFactory") as mock_factory:
            mock_factory.get.return_value = None
            service = EmbeddingService()
            with pytest.raises(RuntimeError, match="not configured|No embedding provider"):
                await service.embed(["test"])

    @pytest.mark.asyncio
    async def test_embed_with_provider(self):
        from app.embeddings import EmbeddingService
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.embed = AsyncMock(
            return_value=[EmbeddingVector(vector=[0.1, 0.2], model="m")]
        )
        with patch("app.providers.factory.ProviderFactory") as mock_factory:
            mock_factory.get.return_value = mock_provider
            service = EmbeddingService()
            results = await service.embed(["hello"])
            assert len(results) == 1
            assert results[0].vector == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_embed_one(self):
        from app.embeddings import EmbeddingService
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.embed = AsyncMock(
            return_value=[EmbeddingVector(vector=[0.3, 0.4], model="m")]
        )
        with patch("app.providers.factory.ProviderFactory") as mock_factory:
            mock_factory.get.return_value = mock_provider
            service = EmbeddingService()
            result = await service.embed_one("hello")
            assert result.vector == [0.3, 0.4]

    @pytest.mark.asyncio
    async def test_embed_empty_list(self):
        from app.embeddings import EmbeddingService
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        with patch("app.providers.factory.ProviderFactory") as mock_factory:
            mock_factory.get.return_value = mock_provider
            service = EmbeddingService()
            results = await service.embed([])
            assert results == []

    @pytest.mark.asyncio
    async def test_embed_with_retry_success(self):
        from app.embeddings import EmbeddingService
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.embed = AsyncMock(
            return_value=[EmbeddingVector(vector=[0.1], model="m")]
        )
        with patch("app.providers.factory.ProviderFactory") as mock_factory:
            mock_factory.get.return_value = mock_provider
            service = EmbeddingService()
            results = await service.embed_with_retry(["test"])
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_embed_with_retry_transient_failure(self):
        from app.embeddings import EmbeddingService
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.embed = AsyncMock(
            side_effect=[
                Exception("timeout"),
                [EmbeddingVector(vector=[0.1], model="m")],
            ]
        )
        with patch("app.providers.factory.ProviderFactory") as mock_factory, \
             patch("asyncio.sleep", new_callable=AsyncMock):
            mock_factory.get.return_value = mock_provider
            service = EmbeddingService()
            results = await service.embed_with_retry(["test"], max_retries=2)
            assert len(results) == 1
            assert mock_provider.embed.call_count == 2

    @pytest.mark.asyncio
    async def test_embed_with_retry_exhausts(self):
        from app.embeddings import EmbeddingService
        mock_provider = MagicMock()
        mock_provider.is_configured = True
        mock_provider.embed = AsyncMock(side_effect=Exception("timeout"))
        with patch("app.providers.factory.ProviderFactory") as mock_factory, \
             patch("asyncio.sleep", new_callable=AsyncMock):
            mock_factory.get.return_value = mock_provider
            service = EmbeddingService()
            with pytest.raises(Exception, match="timeout"):
                await service.embed_with_retry(["test"], max_retries=1)
            assert mock_provider.embed.call_count == 2
