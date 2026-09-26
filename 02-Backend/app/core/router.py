import json
import logging
import os
import random
import re
import time
from typing import Any

from openai import AsyncOpenAI, OpenAI

from .providers import get_active_providers

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.7

_client_cache: dict[str, OpenAI] = {}
_client_ts: dict[str, float] = {}
_CLIENT_TTL = 120.0
_async_client_cache: dict[str, AsyncOpenAI] = {}
_async_client_ts: dict[str, float] = {}
_ASYNC_CLIENT_TTL = 120.0
_RETRY_LIMIT = 3
_RETRY_BASE_DELAY = 0.5


def _get_client_for(provider) -> OpenAI:
    now = time.time()
    cache_key = f"{provider.name}:{provider.base_url}:{os.getenv(provider.env_key, '')}"
    cached = _client_cache.get(cache_key)
    ts = _client_ts.get(cache_key, 0.0)
    if cached is not None and (now - ts) < _CLIENT_TTL:
        return cached
    client = OpenAI(base_url=provider.base_url, api_key=os.getenv(provider.env_key, ""))
    _client_cache[cache_key] = client
    _client_ts[cache_key] = now
    return client


def _get_async_client_for(provider) -> AsyncOpenAI:
    now = time.time()
    cache_key = f"async:{provider.name}:{provider.base_url}:{os.getenv(provider.env_key, '')}"
    cached = _async_client_cache.get(cache_key)
    ts = _async_client_ts.get(cache_key, 0.0)
    if cached is not None and (now - ts) < _ASYNC_CLIENT_TTL:
        return cached
    client = AsyncOpenAI(base_url=provider.base_url, api_key=os.getenv(provider.env_key, ""))
    _async_client_cache[cache_key] = client
    _async_client_ts[cache_key] = now
    return client


def _retryable(func):
    import functools

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        attempt = 0
        while attempt < _RETRY_LIMIT:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                attempt += 1
                if attempt >= _RETRY_LIMIT:
                    raise
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 0.1)
                logger.warning(f"Attempt {attempt} failed for {func.__name__}: {exc}. Retrying in {delay:.2f}s")
                time.sleep(delay)

    return wrapper


def _estimate_confidence(text: str, prompt: str) -> float:
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


_MESSAGES_CACHE: dict[str, list[dict]] = {}
_MESSAGES_TTL = 10.0
_MESSAGES_TS: dict[str, float] = {}


def _build_messages_cached(prompt: str, system: str) -> list[dict]:
    key = f"{prompt}:{system}"
    now = time.time()
    ts = _MESSAGES_TS.get(key, 0.0)
    if key in _MESSAGES_CACHE and (now - ts) < _MESSAGES_TTL:
        return _MESSAGES_CACHE[key]
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if prompt:
        messages.append({"role": "user", "content": prompt})
    _MESSAGES_CACHE[key] = messages
    _MESSAGES_TS[key] = now
    return messages


def _create_chat_completion_with_retry(client, messages: list[dict], provider, timeout: float, tools: list):
    return client.chat.completions.create(
        model=provider.default_model,
        messages=messages,
        timeout=timeout,
        tools=tools,
    )


@_retryable
def call_llm(
    prompt: str = None,
    system: str = "",
    min_confidence: float = None,
    timeout: float = 30,
    tools: list = None,
    messages: list = None,
) -> dict:
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
            client = _get_client_for(provider)
            if messages is None:
                messages = _build_messages_cached(prompt or "", system)
            response = _create_chat_completion_with_retry(client, messages, provider, timeout, tools)

            message = response.choices[0].message
            text = message.content or ""
            tokens = getattr(response.usage, "total_tokens", len((prompt or json.dumps(messages)).split()))
            confidence = _estimate_confidence(text, prompt or "")

            logger.info(
                f"LLM call via {provider.name} ({provider.default_model}) "
                f"confidence={confidence:.2f}"
            )

            result = {
                "text": text,
                "provider": provider.name,
                "model": provider.default_model,
                "tokens": tokens,
                "confidence": confidence,
            }

            tool_calls = getattr(message, "tool_calls", None)
            if tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in tool_calls
                ]

            if confidence >= min_confidence or tool_calls:
                return result

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


async def call_llm_stream(
    prompt: str,
    system: str = "",
    timeout: float = 30,
    tools: list = None,
):
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
            client = _get_async_client_for(provider)
            messages = _build_messages_cached(prompt or "", system)
            stream = client.chat.completions.create(
                model=provider.default_model,
                messages=messages,
                stream=True,
                timeout=timeout,
                tools=tools,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield {
                        "token": delta,
                        "provider": provider.name,
                        "model": provider.default_model,
                    }
            return
        except Exception as e:
            logger.warning(f"Provider {provider.name} streaming failed: {e}")
            errors.append(f"{provider.name}: {e}")
    raise RuntimeError(f"All LLM providers failed: {errors}")


