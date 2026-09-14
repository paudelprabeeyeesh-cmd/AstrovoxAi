import logging
import os
import re

from openai import OpenAI

from .providers import get_active_providers

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7


def estimate_confidence(text: str, prompt: str) -> float:
    """Heuristic confidence score based on response quality."""
    if not text or len(text.strip()) < 10:
        return 0.0
    score = 0.5
    if len(text) > 100:
        score += 0.1
    if "I cannot" in text or "I don't know" in text or "unclear" in text.lower():
        score -= 0.3
    if re.search(r"\b(?:because|therefore|thus|hence)\b", text):
        score += 0.1
    if re.search(r"\b(?:maybe|perhaps|possibly|might)\b", text, re.I):
        score -= 0.1
    return max(0.0, min(1.0, score))


def call_llm(prompt: str, system: str = "", min_confidence: float = None) -> dict:
    if min_confidence is None:
        min_confidence = CONFIDENCE_THRESHOLD

    providers = get_active_providers()
    if not providers:
        raise RuntimeError(
            "No AI provider configured. Set at least one of: "
            "GROQ_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY, "
            "OPENROUTER_API_KEY, HF_API_KEY."
        )

    errors = []
    last_result = None
    
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
            confidence = estimate_confidence(text, prompt)
            
            logger.info(
                f"LLM call via {provider.name} ({provider.default_model}) "
                f"confidence={confidence:.2f}"
            )
            
            last_result = {
                "text": text,
                "provider": provider.name,
                "model": provider.default_model,
                "tokens": tokens,
                "confidence": confidence,
            }
            
            if confidence >= min_confidence:
                return last_result
            
            logger.warning(
                f"Confidence {confidence:.2f} below threshold {min_confidence}, "
                f"trying next provider"
            )
            errors.append(f"{provider.name}: confidence {confidence:.2f} below threshold")
            
        except Exception as e:
            logger.warning(f"Provider {provider.name} failed: {e}")
            errors.append(f"{provider.name}: {e}")

    if last_result:
        logger.warning(f"Returning low-confidence result from {last_result['provider']}")
        return last_result
    
    raise RuntimeError(f"All LLM providers failed: {errors}")
