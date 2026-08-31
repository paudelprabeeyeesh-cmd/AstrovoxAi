"""Anthropic (Claude) provider implementation."""

import os
from typing import Optional, AsyncIterator

from .base import AIProvider, ChatMessage, ChatResponse, ProviderConfig


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider."""

    name = "anthropic"
    supports_streaming = True

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            config = ProviderConfig(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                timeout=120,
                max_retries=2,
            )
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    def validate_model(self, model: str) -> bool:
        from .models import MODELS
        info = MODELS.get(model)
        return info is not None and info.provider == "anthropic"

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        if not self.is_configured:
            raise RuntimeError("Anthropic API key not configured")

        api_messages = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        kwargs = {
            "model": model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if block.type == "text":
                content += block.text

        return ChatResponse(
            content=content,
            model=model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None,
            finish_reason=response.stop_reason,
            provider=self.name,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens from Anthropic."""
        if not self.is_configured:
            raise RuntimeError("Anthropic API key not configured")

        api_messages = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        kwargs = {
            "model": model,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text
