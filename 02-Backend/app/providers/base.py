"""AI Provider Abstraction Layer.

Defines the interface that every provider must implement.
All providers return a consistent ChatResponse format.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, AsyncIterator, Any


@dataclass
class ChatMessage:
    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    provider: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class EmbeddingVector:
    """Result from an embedding request."""
    vector: list[float]
    model: str
    tokens_used: Optional[int] = None


@dataclass
class ProviderConfig:
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60
    max_retries: int = 2


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    name: str = "base"
    supports_streaming: bool = False

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        """Send a chat completion request."""
        ...

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion. Override if provider supports streaming."""
        response = await self.chat(messages, model, temperature, max_tokens, system_prompt)
        yield response.content

    @abstractmethod
    def validate_model(self, model: str) -> bool:
        """Check if a model name is valid for this provider."""
        ...

    async def embed(
        self,
        texts: list[str],
        model: str = "text-embedding-3-small",
    ) -> list[EmbeddingVector]:
        """Generate embeddings for a list of texts. Override if supported."""
        raise NotImplementedError(f"{self.name} does not support embeddings")

    def sanitize_error(self, error: Exception) -> str:
        """Sanitize provider errors to never expose secrets."""
        error_str = str(error)
        sanitized = re.sub(r'(sk-[a-zA-Z0-9]{20,})', '[REDACTED]', error_str)
        sanitized = re.sub(r'(Bearer\s+)[^\s]+', r'\1[REDACTED]', sanitized)
        sanitized = re.sub(r'(sk-ant-[a-zA-Z0-9]{20,})', '[REDACTED]', sanitized)
        sanitized = re.sub(r'(AIza[a-zA-Z0-9_-]{30,})', '[REDACTED]', sanitized)
        if sanitized != error_str:
            return "Provider error (details redacted for security)"
        return error_str

    async def chat_with_retry(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        """Chat with automatic retry on transient failures."""
        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return await self.chat(
                    messages, model, temperature, max_tokens, system_prompt
                )
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
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
                        "overloaded",
                    ]
                )
                if is_transient and attempt < self.config.max_retries:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)
                    continue
                raise
        raise last_error  # Should not reach here
