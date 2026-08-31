"""Provider factory — creates and manages AI provider instances."""

import os
from typing import Optional

from .base import AIProvider, ProviderConfig
from .models import get_provider_for_model, is_valid_model, list_models


class ProviderFactory:
    """Factory for creating AI provider instances."""

    _providers: dict[str, AIProvider] = {}

    @classmethod
    def register(cls, name: str, provider: AIProvider):
        """Register a provider instance."""
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str) -> Optional[AIProvider]:
        """Get a provider by name."""
        return cls._providers.get(name)

    @classmethod
    def get_for_model(cls, model_id: str) -> Optional[AIProvider]:
        """Get the appropriate provider for a model."""
        provider_name = get_provider_for_model(model_id)
        if not provider_name:
            return None
        return cls._providers.get(provider_name)

    @classmethod
    def list_configured(cls) -> list[str]:
        """List names of all configured providers."""
        return [name for name, p in cls._providers.items() if p.is_configured]

    @classmethod
    def clear(cls):
        """Clear all registered providers (for testing)."""
        cls._providers.clear()


def _initialize_providers():
    """Initialize all providers from environment variables."""
    from .openai_provider import OpenAIProvider
    from .anthropic_provider import AnthropicProvider
    from .gemini_provider import GeminiProvider
    from .ollama_provider import OllamaProvider

    # OpenAI
    openai = OpenAIProvider()
    if openai.is_configured:
        ProviderFactory.register("openai", openai)

    # Anthropic
    anthropic = AnthropicProvider()
    if anthropic.is_configured:
        ProviderFactory.register("anthropic", anthropic)

    # Gemini
    gemini = GeminiProvider()
    if gemini.is_configured:
        ProviderFactory.register("gemini", gemini)

    # Ollama (always available if server is running)
    ollama = OllamaProvider()
    ProviderFactory.register("ollama", ollama)


# Auto-initialize on import
_initialize_providers()
