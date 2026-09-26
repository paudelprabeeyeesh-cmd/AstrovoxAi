"""Python SDK client template."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx


class AstrovoxError(Exception):
    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status


class AstrovoxClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0, max_retries: int = 3) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method=method, url=url, json=body, headers=self._headers())
        if response.status_code >= 400:
            raise AstrovoxError(response.text, status=response.status_code)
        if response.status_code == 204:
            return None
        return response.json()
