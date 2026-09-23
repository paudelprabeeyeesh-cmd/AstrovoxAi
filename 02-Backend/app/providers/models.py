"""Model registry — maps model names to providers and validates availability."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelInfo:
    id: str
    provider: str
    display_name: str
    supports_streaming: bool = True
    max_tokens: int = 4096
    description: str = ""


# ============================================================================
# Model Registry
# ============================================================================

MODELS: dict[str, ModelInfo] = {
    # OpenAI
    "gpt-4": ModelInfo("gpt-4", "openai", "GPT-4", True, 8192, "Most capable GPT-4 model"),
    "gpt-4o-mini": ModelInfo("gpt-4o-mini", "openai", "GPT-4o Mini", True, 16384, "Fast and affordable"),
    "gpt-3.5-turbo": ModelInfo("gpt-3.5-turbo", "openai", "GPT-3.5 Turbo", True, 4096, "Fast and inexpensive"),

    # Anthropic
    "claude-3-5-sonnet": ModelInfo("claude-3-5-sonnet-20241022", "anthropic", "Claude 3.5 Sonnet", True, 8192, "Most intelligent Claude"),
    "claude-3-opus": ModelInfo("claude-3-opus-20240229", "anthropic", "Claude 3 Opus", True, 4096, "Powerful Claude 3"),
    "claude-3-haiku": ModelInfo("claude-3-haiku-20240307", "anthropic", "Claude 3 Haiku", True, 4096, "Fastest Claude 3"),

    # Google Gemini
    "gemini-1.5-pro": ModelInfo("gemini-1.5-pro", "gemini", "Gemini 1.5 Pro", True, 8192, "Most capable Gemini"),
    "gemini-1.5-flash": ModelInfo("gemini-1.5-flash", "gemini", "Gemini 1.5 Flash", True, 8192, "Fast and efficient"),
    "gemini-1.0-pro": ModelInfo("gemini-1.0-pro", "gemini", "Gemini 1.0 Pro", True, 4096, "First generation Gemini"),

    # Ollama (local)
    "llama3": ModelInfo("llama3", "ollama", "Llama 3 (Local)", False, 4096, "Meta Llama 3 via Ollama"),
    "llama3.1": ModelInfo("llama3.1", "ollama", "Llama 3.1 (Local)", False, 4096, "Meta Llama 3.1 via Ollama"),
    "mistral": ModelInfo("mistral", "ollama", "Mistral (Local)", False, 4096, "Mistral via Ollama"),
    "mixtral": ModelInfo("mixtral", "ollama", "Mixtral (Local)", False, 4096, "Mixtral via Ollama"),
    "codellama": ModelInfo("codellama", "ollama", "Code Llama (Local)", False, 4096, "Code Llama via Ollama"),
    "phi3": ModelInfo("phi3", "ollama", "Phi-3 (Local)", False, 4096, "Microsoft Phi-3 via Ollama"),
    "gemma2": ModelInfo("gemma2", "ollama", "Gemma 2 (Local)", False, 4096, "Google Gemma 2 via Ollama"),
}


def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """Get model info by ID."""
    return MODELS.get(model_id)


def get_provider_for_model(model_id: str) -> Optional[str]:
    """Get the provider name for a given model."""
    info = MODELS.get(model_id)
    return info.provider if info else None


def is_valid_model(model_id: str) -> bool:
    """Check if a model ID is supported."""
    return model_id in MODELS


def list_models(provider: Optional[str] = None) -> list[ModelInfo]:
    """List all supported models, optionally filtered by provider."""
    models = list(MODELS.values())
    if provider:
        models = [m for m in models if m.provider == provider]
    return sorted(models, key=lambda m: (m.provider, m.display_name))
