"""Adapter layer for TensorRT-LLM, vLLM, and llama.cpp backends."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional

logger = logging.getLogger(__name__)


@dataclass
class AdapterRequest:
    prompt: str
    max_tokens: int = 256
    temperature: float = 1.0
    top_p: float = 0.9
    top_k: Optional[int] = None
    stop_sequences: Optional[list[str]] = None
    stream: bool = False
    model: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AdapterResponse:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    metadata: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class BaseInferenceAdapter(ABC):
    @abstractmethod
    def generate(self, request: AdapterRequest) -> AdapterResponse:
        raise NotImplementedError

    @abstractmethod
    async def stream(self, request: AdapterRequest) -> AsyncGenerator[str, None]:
        raise NotImplementedError

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_model_name(self) -> str:
        raise NotImplementedError


class TensorRTLLMAdapter(BaseInferenceAdapter):
    def __init__(self, host: str = "http://localhost:8001", model: str = "tensorrt-llm"):
        self._base_url = host.rstrip("/")
        self._model = model

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        import httpx
        payload = {
            "model": request.model or self._model,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": False,
        }
        start = __import__("time").time()
        with httpx.Client(timeout=120) as client:
            response = client.post(f"{self._base_url}/v1/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        latency = (__import__("time").time() - start) * 1000
        text = data.get("choices", [{}])[0].get("text", "")
        usage = data.get("usage", {})
        return AdapterResponse(
            text=text,
            model=request.model or self._model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency,
            finish_reason=data.get("choices", [{}])[0].get("finish_reason", "stop"),
        )

    async def stream(self, request: AdapterRequest):
        import httpx
        import json as json_mod
        payload = {
            "model": request.model or self._model,
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{self._base_url}/v1/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip() and line.startswith("data:"):
                        data_str = line.replace("data:", "").strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json_mod.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("text", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def health_check(self) -> bool:
        import httpx
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self._base_url}/health")
                return response.status_code == 200
        except Exception:
            return False

    def get_model_name(self) -> str:
        return self._model


class VLLMAdapter(BaseInferenceAdapter):
    def __init__(self, host: str = "http://localhost:8000", model: str = "meta-llama/Llama-2-7b-chat-hf"):
        self._base_url = host.rstrip("/")
        self._model = model

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        import httpx
        messages = [{"role": "user", "content": request.prompt}]
        if request.stop_sequences:
            payload_stop = request.stop_sequences
        else:
            payload_stop = None
        payload = {
            "model": request.model or self._model,
            "messages": messages,
            "stream": False,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "stop": payload_stop,
        }
        start = __import__("time").time()
        with httpx.Client(timeout=120) as client:
            response = client.post(f"{self._base_url}/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        latency = (__import__("time").time() - start) * 1000
        choice = data.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return AdapterResponse(
            text=text,
            model=request.model or self._model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency,
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def stream(self, request: AdapterRequest):
        import httpx
        import json as json_mod
        messages = [{"role": "user", "content": request.prompt}]
        payload = {
            "model": request.model or self._model,
            "messages": messages,
            "stream": True,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "stop": request.stop_sequences,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{self._base_url}/v1/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip() and line.startswith("data:"):
                        data_str = line.replace("data:", "").strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json_mod.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def health_check(self) -> bool:
        import httpx
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self._base_url}/health")
                return response.status_code == 200
        except Exception:
            return False

    def get_model_name(self) -> str:
        return self._model


class LlamaCppAdapter(BaseInferenceAdapter):
    def __init__(self, host: str = "http://localhost:8080", model: str = "llama-cpp"):
        self._base_url = host.rstrip("/")
        self._model = model

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        import httpx
        payload = {
            "model": request.model or self._model,
            "prompt": request.prompt,
            "n_predict": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stop": request.stop_sequences or [],
            "stream": False,
        }
        start = __import__("time").time()
        with httpx.Client(timeout=120) as client:
            response = client.post(f"{self._base_url}/completion", json=payload)
            response.raise_for_status()
            data = response.json()
        latency = (__import__("time").time() - start) * 1000
        text = data.get("content", "")
        usage = data.get("tokens_predicted", 0)
        return AdapterResponse(
            text=text,
            model=request.model or self._model,
            completion_tokens=usage,
            latency_ms=latency,
        )

    async def stream(self, request: AdapterRequest):
        import httpx
        import json as json_mod
        payload = {
            "model": request.model or self._model,
            "prompt": request.prompt,
            "n_predict": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stop": request.stop_sequences or [],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", f"{self._base_url}/completion", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json_mod.loads(line)
                            content = data.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def health_check(self) -> bool:
        import httpx
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self._base_url}/health")
                return response.status_code == 200
        except Exception:
            return False

    def get_model_name(self) -> str:
        return self._model
