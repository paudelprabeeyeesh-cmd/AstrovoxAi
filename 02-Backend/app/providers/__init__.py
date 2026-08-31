"""AI Provider Abstraction Layer.

Supports: OpenAI, Anthropic (Claude), Google Gemini, Ollama (local).
"""

from .base import AIProvider, ChatMessage, ChatResponse, ProviderConfig
from .models import (
    ModelInfo,
    MODELS,
    get_model_info,
    get_provider_for_model,
    is_valid_model,
    list_models,
)
from .factory import ProviderFactory
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider

__all__ = [
    "AIProvider",
    "ChatMessage",
    "ChatResponse",
    "ProviderConfig",
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
