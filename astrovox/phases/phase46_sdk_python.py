"""Official Python SDK for Astrovox API."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError


@dataclass
class SDKConfig:
    """SDK configuration."""
    api_key: str = ""
    base_url: str = "https://api.astrovox.ai/v1"
    timeout: float = 30.0


class AstrovoxSDK:
    """Official Astrovox Python SDK."""

    def __init__(self, config: SDKConfig | str | None = None, api_key: str = ""):
        if isinstance(config, SDKConfig):
            self.config = config
        else:
            self.config = SDKConfig(api_key=api_key or config or "")
        self._headers = {"Authorization": f"Bearer {self.config.api_key}",
                         "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.config.base_url}{path}"
        data = kwargs.pop("data", None)
        headers = {**self._headers, **kwargs.pop("headers", {})}
        req = Request(url, data=data.encode() if isinstance(data, str) else data,
                      headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode())
        except URLError as e:
            raise RuntimeError(f"API request failed: {e}")

    def chat(self, messages: list[dict], model: str = "astrovox", stream: bool = False) -> Any:
        """Send a chat request."""
        return self._request("POST", "/chat", data=json.dumps({"messages": messages, "model": model,
                                                                "stream": stream}))

    def embed(self, text: str, model: str = "astrovox-embed") -> list[float]:
        """Get an embedding for text."""
        resp = self._request("POST", "/embeddings", data=json.dumps({"input": text, "model": model}))
        return resp.get("embedding", [])

    def search(self, query: str, **kwargs) -> dict:
        """Search with the RAG engine."""
        params = {"q": query, **kwargs}
        return self._request("GET", "/search", params=params)

    def transcribe(self, audio: bytes, language: str = "en") -> str:
        """Transcribe audio to text."""
        return self._request("POST", "/transcribe", data=audio)

    def versions(self) -> dict:
        """List available models."""
        return self._request("GET", "/models")

    def health(self) -> dict:
        """Check API health."""
        return self._request("GET", "/health")
