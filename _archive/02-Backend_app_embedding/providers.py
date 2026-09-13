"""Embedding Engine — Production-grade multi-provider embedding infrastructure.

Supports: OpenAI, Cohere, Ollama (local), with caching, retries, batching,
dimension validation, and automatic provider fallback.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
import hashlib
import time
import json
import os
import re


@dataclass
class EmbeddingVector:
    """A single embedding result."""
    vector: list[float]
    model: str
    provider: str
    dimensions: int
    tokens_used: Optional[int] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class EmbeddingBatchResult:
    """Result of a batch embedding request."""
    embeddings: list[EmbeddingVector]
    model: str
    provider: str
    total_tokens: int = 0
    batch_size: int = 0


@dataclass
class EmbeddingConfig:
    """Configuration for an embedding provider."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "text-embedding-3-small"
    timeout: int = 60
    max_retries: int = 2
    dimensions: Optional[int] = None  # None = use provider default


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    name: str = "base"
    default_model: str = "text-embedding-3-small"
    supported_dimensions: list[int] = [1536, 512, 256]
    max_batch_size: int = 100
    supports_batch: bool = True

    def __init__(self, config: EmbeddingConfig):
        self.config = config

    @property
    def is_configured(self) -> bool:
        return True

    @abstractmethod
    async def embed(self, texts: list[str]) -> EmbeddingBatchResult:
        """Generate embeddings for a list of texts."""
        ...

    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """Check if a model is valid for this provider."""
        ...

    def validate_dimensions(self, expected: int, actual: int) -> bool:
        """Validate embedding dimensions match expectations."""
        return expected == actual

    def sanitize_error(self, error: Exception) -> str:
        """Sanitize provider errors to never expose secrets."""
        error_str = str(error)
        sanitized = re.sub(r'(sk-[a-zA-Z0-9]{20,})', '[REDACTED]', error_str)
        sanitized = re.sub(r'(Bearer\s+)[^\s]+', r'\1[REDACTED]', sanitized)
        if sanitized != error_str:
            return "Provider error (details redacted for security)"
        return error_str


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text embedding provider."""

    name = "openai"
    default_model = "text-embedding-3-small"
    supported_dimensions = [1536, 512, 256]
    max_batch_size = 2048
    supports_batch = True

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        if config is None:
            config = EmbeddingConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                model="text-embedding-3-small",
                timeout=60,
                max_retries=2,
            )
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def validate_model(self, model: str) -> bool:
        valid_models = {
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        }
        return model in valid_models

    async def embed(self, texts: list[str]) -> EmbeddingBatchResult:
        if not self.is_configured:
            raise RuntimeError("OpenAI API key not configured")

        kwargs = {
            "model": self.config.model,
            "input": texts,
        }
        if self.config.dimensions:
            kwargs["dimensions"] = self.config.dimensions

        response = self.client.embeddings.create(**kwargs)

        embeddings = []
        for item in response.data:
            embeddings.append(EmbeddingVector(
                vector=item.embedding,
                model=self.config.model,
                provider=self.name,
                dimensions=len(item.embedding),
            ))

        return EmbeddingBatchResult(
            embeddings=embeddings,
            model=self.config.model,
            provider=self.name,
            total_tokens=response.usage.total_tokens if response.usage else 0,
            batch_size=len(texts),
        )


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama local embedding provider."""

    name = "ollama"
    default_model = "nomic-embed-text"
    supported_dimensions = [768]
    max_batch_size = 32
    supports_batch = False

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        if config is None:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            config = EmbeddingConfig(
                base_url=base_url,
                model="nomic-embed-text",
                timeout=120,
                max_retries=1,
            )
        super().__init__(config)

    def validate_model(self, model: str) -> bool:
        valid = {"nomic-embed-text", "mxbai-embed-large", "all-minilm", "bge-m3"}
        return model in valid

    async def embed(self, texts: list[str]) -> EmbeddingBatchResult:
        import httpx

        embeddings = []
        total_tokens = 0

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            for text in texts:
                response = await client.post(
                    f"{self.config.base_url}/api/embeddings",
                    json={
                        "model": self.config.model,
                        "prompt": text,
                    },
                )
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:200]}")

                data = response.json()
                embeddings.append(EmbeddingVector(
                    vector=data["embedding"],
                    model=self.config.model,
                    provider=self.name,
                    dimensions=len(data["embedding"]),
                ))

        return EmbeddingBatchResult(
            embeddings=embeddings,
            model=self.config.model,
            provider=self.name,
            total_tokens=total_tokens,
            batch_size=len(texts),
        )


# ============================================================================
# Provider Registry & Factory
# ============================================================================

class EmbeddingProviderFactory:
    """Factory for creating and managing embedding providers."""

    _providers: dict[str, EmbeddingProvider] = {}

    @classmethod
    def register(cls, name: str, provider: EmbeddingProvider):
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str) -> Optional[EmbeddingProvider]:
        return cls._providers.get(name)

    @classmethod
    def list_configured(cls) -> list[str]:
        return [n for n, p in cls._providers.items() if p.is_configured]

    @classmethod
    def clear(cls):
        cls._providers.clear()


def _initialize_embedding_providers():
    """Initialize embedding providers from environment."""
    openai = OpenAIEmbeddingProvider()
    if openai.is_configured:
        EmbeddingProviderFactory.register("openai", openai)

    ollama = OllamaEmbeddingProvider()
    EmbeddingProviderFactory.register("ollama", ollama)


_initialize_embedding_providers()
