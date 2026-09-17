import logging
import json
from typing import AsyncGenerator

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import BaseLLMAdapter

logger = logging.getLogger(__name__)


class HuggingFaceAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str = "", model: str = "meta-llama/Llama-2-7b-chat-hf"):
        self._api_key = api_key
        self._model = model
        self._base_url = "https://router.huggingface.co/v1"

    def get_model_name(self) -> str:
        return self._model

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def health_check(self) -> bool:
        try:
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            with httpx.Client(timeout=5) as client:
                response = client.get(
                    f"https://huggingface.co/api/models/{self._model}",
                    headers=headers,
                )
                return response.status_code == 200
        except Exception:
            return False

    def route_model(self, task: str = "text-generation") -> str:
        routing = {
            "text-generation": "text-generation",
            "chat": "conversational",
            "code": "code-generation",
            "embedding": "feature-extraction",
        }
        endpoint = routing.get(task, "text-generation")
        return f"{self._base_url}/{endpoint}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    def generate(self, prompt: str, **kwargs) -> str:
        system = kwargs.get("system", "")
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2048)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {"model": self._model, "messages": messages, "stream": False, "temperature": temperature, "max_tokens": max_tokens}
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{self._base_url}/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        system = kwargs.get("system", "")
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2048)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {"model": self._model, "messages": messages, "stream": True, "temperature": temperature, "max_tokens": max_tokens}
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{self._base_url}/chat/completions", json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip() and line.startswith("data:"):
                        data_str = line.replace("data:", "").strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue
