import logging
import time
from typing import AsyncGenerator

import google.generativeai as genai
from google.generativeai.types import generation_types

from .base import BaseLLMAdapter

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = {"gemini-2.5-flash", "gemini-1.5-pro"}

RETRYABLE_ERRORS = (
    generation_types.BlockedPromptException,
    generation_types.StopCandidateException,
    TimeoutError,
)


class GeminiAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if model not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported Gemini model: {model}. Supported: {sorted(SUPPORTED_MODELS)}"
            )
        self._model = model
        genai.configure(api_key=api_key)
        self._client = genai.GenerativeModel(model)

    def get_model_name(self) -> str:
        return self._model

    def count_tokens(self, text: str) -> int:
        try:
            return self._client.count_tokens(text).total_tokens
        except Exception:
            return max(1, len(text) // 4)

    def generate(self, prompt: str, **kwargs) -> str:
        max_retries = kwargs.get("max_retries", 3)
        timeout = kwargs.get("timeout", 30)
        system = kwargs.get("system", "")
        tools = kwargs.get("tools")

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                response = self._client.generate_content(
                    [system, prompt] if system else prompt,
                    generation_config={
                        "temperature": kwargs.get("temperature", 0.7),
                        "max_output_tokens": kwargs.get("max_tokens", 4096),
                    },
                    tools=tools,
                )
                return response.text or ""
            except RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "Gemini generate attempt %s/%s failed: %s", attempt, max_retries, exc
                )
                time.sleep(2 ** attempt)
        raise RuntimeError(
            f"Gemini generate failed after {max_retries} attempts: {last_error}"
        )

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        max_retries = kwargs.get("max_retries", 3)
        timeout = kwargs.get("timeout", 30)
        system = kwargs.get("system", "")
        tools = kwargs.get("tools")

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                response = self._client.generate_content(
                    [system, prompt] if system else prompt,
                    generation_config={
                        "temperature": kwargs.get("temperature", 0.7),
                        "max_output_tokens": kwargs.get("max_tokens", 4096),
                    },
                    stream=True,
                    tools=tools,
                )
                for chunk in response:
                    yield chunk.text or ""
                return
            except RETRYABLE_ERRORS as exc:
                last_error = exc
                logger.warning(
                    "Gemini stream attempt %s/%s failed: %s", attempt, max_retries, exc
                )
                time.sleep(2 ** attempt)
        raise RuntimeError(
            f"Gemini stream failed after {max_retries} attempts: {last_error}"
        )
