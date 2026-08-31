"""Ollama (local models) provider implementation."""

import os
import json
import httpx
from typing import Optional

from .base import AIProvider, ChatMessage, ChatResponse, ProviderConfig


class OllamaProvider(AIProvider):
    """Ollama local models provider."""

    name = "ollama"
    supports_streaming = True

    def __init__(self, config: Optional[ProviderConfig] = None):
        if config is None:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            config = ProviderConfig(
                api_key=None,
                base_url=base_url,
                timeout=300,
                max_retries=1,
            )
        super().__init__(config)

    @property
    def is_configured(self) -> bool:
        """Ollama doesn't need an API key — just a running server."""
        return True

    def validate_model(self, model: str) -> bool:
        from .models import MODELS
        info = MODELS.get(model)
        return info is not None and info.provider == "ollama"

    async def _check_server(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.config.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
    ) -> ChatResponse:
        if not await self._check_server():
            raise RuntimeError(
                "Ollama server not reachable. Start Ollama with: ollama serve"
            )

        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend([{"role": m.role, "content": m.content} for m in messages])

        payload = {
            "model": model,
            "messages": api_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.base_url}/api/chat",
                json=payload,
            )

            if response.status_code != 200:
                raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:200]}")

            data = response.json()

        return ChatResponse(
            content=data.get("message", {}).get("content", ""),
            model=model,
            tokens_used=data.get("eval_count"),
            finish_reason="stop" if not data.get("done") else data.get("done_reason"),
            provider=self.name,
            metadata={
                "total_duration": data.get("total_duration"),
                "load_duration": data.get("load_duration"),
                "prompt_eval_count": data.get("prompt_eval_count"),
            },
        )

    async def list_local_models(self) -> list[str]:
        """List models available on the local Ollama server."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.config.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []
