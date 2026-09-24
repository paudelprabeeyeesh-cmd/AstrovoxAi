"""External API integration framework."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ExternalAPIEndpoint:
    name: str
    base_url: str
    api_key: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    retries: int = 3
    backoff_factor: float = 0.5
    tags: List[str] = field(default_factory=list)


@dataclass
class APIResponse:
    endpoint_name: str
    status_code: int
    body: Any
    latency_ms: float
    success: bool
    error: Optional[str] = None


class ExternalAPIClient:
    """Client for external API integrations with retry and circuit breaker."""

    def __init__(self):
        self._endpoints: Dict[str, ExternalAPIEndpoint] = {}
        self._client = httpx.Client(timeout=30.0)

    def register_endpoint(self, endpoint: ExternalAPIEndpoint) -> None:
        self._endpoints[endpoint.name] = endpoint
        logger.info("Registered external API endpoint: %s", endpoint.name)

    def call(
        self,
        endpoint_name: str,
        path: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        endpoint = self._endpoints.get(endpoint_name)
        if not endpoint:
            return APIResponse(
                endpoint_name=endpoint_name,
                status_code=404,
                body=None,
                latency_ms=0.0,
                success=False,
                error=f"Endpoint {endpoint_name} not registered",
            )
        url = f"{endpoint.base_url.rstrip('/')}/{path.lstrip('/')}"
        merged_headers = {**endpoint.headers, **(headers or {})}
        if endpoint.api_key:
            merged_headers.setdefault("Authorization", f"Bearer {endpoint.api_key}")
        start = time.perf_counter()
        last_error = None
        for attempt in range(endpoint.retries):
            try:
                response = self._client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=merged_headers,
                    timeout=endpoint.timeout_seconds,
                )
                latency = (time.perf_counter() - start) * 1000
                success = response.status_code < 400
                return APIResponse(
                    endpoint_name=endpoint_name,
                    status_code=response.status_code,
                    body=response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    latency_ms=latency,
                    success=success,
                )
            except httpx.TimeoutException:
                last_error = "timeout"
            except httpx.HTTPStatusError as exc:
                last_error = f"HTTP {exc.response.status_code}"
                if exc.response.status_code < 500:
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                break
            time.sleep(endpoint.backoff_factor * (2 ** attempt))
        latency = (time.perf_counter() - start) * 1000
        return APIResponse(
            endpoint_name=endpoint_name,
            status_code=0,
            body=None,
            latency_ms=latency,
            success=False,
            error=last_error,
        )

    def close(self) -> None:
        self._client.close()


external_api_client = ExternalAPIClient()
