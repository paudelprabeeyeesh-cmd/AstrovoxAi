import os
import logging
from openai import OpenAI
from .providers import get_active_providers

logger = logging.getLogger(__name__)


def call_llm(prompt: str, system: str = "") -> dict:
    providers = get_active_providers()
    if not providers:
        raise RuntimeError(
            "No AI provider configured. Set at least one of: "
            "GROQ_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY, "
            "OPENROUTER_API_KEY, HF_API_KEY."
        )

    errors = []
    for provider in providers:
        api_key = os.getenv(provider.env_key)
        if not api_key:
            continue
        try:
            client = OpenAI(base_url=provider.base_url, api_key=api_key)
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=provider.default_model,
                messages=messages,
                timeout=15,
            )
            text = response.choices[0].message.content or ""
            tokens = getattr(response.usage, "total_tokens", len(prompt.split()))
            logger.info(f"LLM call succeeded via {provider.name} using {provider.default_model}")
            return {
                "text": text,
                "provider": provider.name,
                "model": provider.default_model,
                "tokens": tokens,
            }
        except Exception as e:
            logger.warning(f"Provider {provider.name} failed: {e}")
            errors.append(f"{provider.name}: {e}")

    raise RuntimeError(f"All LLM providers failed: {errors}")
