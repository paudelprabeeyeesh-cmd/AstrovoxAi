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

    def sanitize_error(self, error: Exception) -> str:
        """Sanitize provider errors to never expose secrets."""
        error_str = str(error)
        # Remove potential API keys from error messages
        import re
        sanitized = re.sub(r'(sk-[a-zA-Z0-9]{20,})', '[REDACTED]', error_str)
        sanitized = re.sub(r'(Bearer\s+)[^\s]+', r'\1[REDACTED]', sanitized)
        if sanitized != error_str:
            return "Provider error (details redacted for security)"
        return error_str
