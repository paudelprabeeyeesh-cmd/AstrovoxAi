import logging
import time
from typing import AsyncGenerator

from openai import OpenAI, OpenAIError

from .base import BaseLLMAdapter

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo"}

RETRYABLE_ERRORS = (
    OpenAIError,
    TimeoutError,
)


class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if model not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported OpenAI model: {model}. Supported: {sorted(SUPPORTED_MODELS)}"
            )
        self._model = model
        self._client = OpenAI(api_key=api_key)

    def get_model_name(self) -> str:
        return self._model

    def count_tokens(self, text: str) -> int:
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self._model)
            return len(encoding.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def generate(self, prompt: str, **kwargs) -> str:
        max_retries = kwargs.get("max_retries", 3)
        timeout = kwargs.get("timeout", 30)
        system = kwargs.get("system", "")
        tools = kwargs.get("tools")
        messages = kwargs.get("messages")

        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    timeout=timeout,
                    tools=tools,
                )
                return response.choices[0].message.content or ""
            except RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "OpenAI generate attempt %s/%s failed: %s", attempt, max_retries, exc
                )
                time.sleep(2 ** attempt)
        raise RuntimeError(
            f"OpenAI generate failed after {max_retries} attempts: {last_error}"
        )

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        max_retries = kwargs.get("max_retries", 3)
        timeout = kwargs.get("timeout", 30)
        system = kwargs.get("system", "")
        tools = kwargs.get("tools")
        messages = kwargs.get("messages")

        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                stream = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    stream=True,
                    timeout=timeout,
                    tools=tools,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        yield delta
                return
            except RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "OpenAI stream attempt %s/%s failed: %s", attempt, max_retries, exc
                )
                time.sleep(2 ** attempt)
        raise RuntimeError(
            f"OpenAI stream failed after {max_retries} attempts: {last_error}"
        )
