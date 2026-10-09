"""AI Provider Abstraction Layer.

Supports: OpenAI, Anthropic (Claude), Google Gemini, Ollama (local).
"""

from .base import AIProvider, ChatMessage, ChatResponse, ProviderConfig, EmbeddingVector  # noqa: F401
from .models import (
    ModelInfo,
    MODELS,
    get_model_info,
    get_provider_for_model,
    is_valid_model,
    list_models,
)
from .factory import ProviderFactory  # noqa: F401
from .openai_provider import OpenAIProvider  # noqa: F401
from .anthropic_provider import AnthropicProvider  # noqa: F401
from .gemini_provider import GeminiProvider  # noqa: F401
from .ollama_provider import OllamaProvider  # noqa: F401

__all__ = [
    "AIProvider",
    "ChatMessage",
    "ChatResponse",
    "ProviderConfig",
    "EmbeddingVector",
    "ModelInfo",
    "MODELS",
    "get_model_info",
    "get_provider_for_model",
    "is_valid_model",
    "list_models",
    "ProviderFactory",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
]
