import logging
import time
from typing import AsyncGenerator

import anthropic
from anthropic import AnthropicError

from .base import BaseLLMAdapter

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = {"claude-3-5-sonnet", "claude-3-haiku"}

RETRYABLE_ERRORS = (
    AnthropicError,
    TimeoutError,
)


class AnthropicAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet"):
        if model not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported Anthropic model: {model}. Supported: {sorted(SUPPORTED_MODELS)}"
            )
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    def get_model_name(self) -> str:
        return self._model

    def count_tokens(self, text: str) -> int:
        try:
            return self._client.count_tokens(text).input_tokens
        except Exception:
            return max(1, len(text) // 4)

    def generate(self, prompt: str, **kwargs) -> str:
        max_retries = kwargs.get("max_retries", 3)
        timeout = kwargs.get("timeout", 30)
        system = kwargs.get("system", "")
        tools = kwargs.get("tools")
        messages = kwargs.get("messages")

        if messages is None:
            messages = [{"role": "user", "content": prompt}]

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                message = self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    system=system,
                    messages=messages,
                    timeout=timeout,
                    tools=tools,
                )
                return message.content[0].text if message.content else ""
            except RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "Anthropic generate attempt %s/%s failed: %s", attempt, max_retries, exc
                )
                time.sleep(2 ** attempt)
        raise RuntimeError(
            f"Anthropic generate failed after {max_retries} attempts: {last_error}"
        )

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        max_retries = kwargs.get("max_retries", 3)
        timeout = kwargs.get("timeout", 30)
        system = kwargs.get("system", "")
        tools = kwargs.get("tools")
        messages = kwargs.get("messages")

        if messages is None:
            messages = [{"role": "user", "content": prompt}]

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                with self._client.messages.stream(
                    model=self._model,
                    max_tokens=4096,
                    system=system,
                    messages=messages,
                    timeout=timeout,
                    tools=tools,
                ) as stream:
                    for text in stream.text_stream:
                        yield text
                return
            except RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "Anthropic stream attempt %s/%s failed: %s", attempt, max_retries, exc
                )
                time.sleep(2 ** attempt)
        raise RuntimeError(
            f"Anthropic stream failed after {max_retries} attempts: {last_error}"
        )
