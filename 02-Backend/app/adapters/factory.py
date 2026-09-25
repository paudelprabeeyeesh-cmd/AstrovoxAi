import logging
import os

from app.adapters.anthropic_adapter import AnthropicAdapter
from app.adapters.base import BaseLLMAdapter
from app.adapters.gemini_adapter import GeminiAdapter
from app.adapters.groq_adapter import GroqAdapter
from app.adapters.huggingface_adapter import HuggingFaceAdapter
from app.adapters.ollama_adapter import OllamaAdapter
from app.adapters.openai_adapter import OpenAIAdapter
from app.adapters.vllm_adapter import VLLMAdapter

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {"openai", "anthropic", "gemini", "groq", "huggingface", "ollama", "vllm"}

_PROVIDER_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "huggingface": "HF_API_KEY",
}

_cache: dict[str, BaseLLMAdapter] = {}


def _cache_key(provider: str, model: str) -> str:
    return f"{provider}:{model}"


def get_adapter(provider: str, model: str, host: str = "") -> BaseLLMAdapter:
    key = _cache_key(provider, model)
    if key in _cache:
        return _cache[key]

    provider = provider.lower().strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported provider: {provider}. Supported: {sorted(SUPPORTED_PROVIDERS)}"
        )

    adapter: BaseLLMAdapter
    if provider == "openai":
        env_key = _PROVIDER_ENV_KEYS[provider]
        api_key = os.getenv(env_key)
        if not api_key:
            raise RuntimeError(f"Missing API key for provider '{provider}'. Set the {env_key} environment variable.")
        adapter = OpenAIAdapter(api_key=api_key, model=model)
    elif provider == "anthropic":
        env_key = _PROVIDER_ENV_KEYS[provider]
        api_key = os.getenv(env_key)
        if not api_key:
            raise RuntimeError(f"Missing API key for provider '{provider}'. Set the {env_key} environment variable.")
        adapter = AnthropicAdapter(api_key=api_key, model=model)
    elif provider == "gemini":
        env_key = _PROVIDER_ENV_KEYS[provider]
        api_key = os.getenv(env_key)
        if not api_key:
            raise RuntimeError(f"Missing API key for provider '{provider}'. Set the {env_key} environment variable.")
        adapter = GeminiAdapter(api_key=api_key, model=model)
    elif provider == "groq":
        env_key = _PROVIDER_ENV_KEYS[provider]
        api_key = os.getenv(env_key)
        if not api_key:
            raise RuntimeError(f"Missing API key for provider '{provider}'. Set the {env_key} environment variable.")
        adapter = GroqAdapter(api_key=api_key, model=model)
    elif provider == "huggingface":
        env_key = _PROVIDER_ENV_KEYS[provider]
        api_key = os.getenv(env_key, "")
        adapter = HuggingFaceAdapter(api_key=api_key, model=model)
    elif provider == "ollama":
        host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        adapter = OllamaAdapter(host=host, model=model)
    elif provider == "vllm":
        host = host or os.getenv("VLLM_HOST", "http://localhost:8000")
        adapter = VLLMAdapter(host=host, model=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    logger.info("Created adapter for %s model=%s", provider, model)
    _cache[key] = adapter
    return adapter


def health_check(provider: str, model: str, host: str = "") -> bool:
    try:
        adapter = get_adapter(provider, model, host=host)
        if hasattr(adapter, "health_check"):
            return adapter.health_check()
        return True
    except Exception as e:
        logger.error("Health check failed for %s/%s: %s", provider, model, e)
        return False
