"""
Unified API gateway integration.

Manages multiple API providers, circuit breakers, retries, and request/response transformations.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple


class ProviderStatus(Enum):
    AVAILABLE = auto()
    DEGRADED = auto()
    UNAVAILABLE = auto()


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


@dataclass
class APIProvider:
    name: str
    base_url: str
    timeout: float = 30.0
    retries: int = 3
    status: ProviderStatus = ProviderStatus.AVAILABLE
    circuit: CircuitState = CircuitState.CLOSED
    failure_threshold: int = 5
    success_threshold: int = 2
    failures: int = 0
    successes: int = 0
    last_failure: float = 0.0
    half_open_interval: float = 15.0


@dataclass
class CircuitBreaker:
    provider: APIProvider

    def allow_request(self) -> bool:
        if self.provider.circuit == CircuitState.CLOSED:
            return True
        if self.provider.circuit == CircuitState.HALF_OPEN:
            return time.time() - self.provider.last_failure >= self.provider.half_open_interval
        return False

    def record_success(self) -> None:
        self.provider.successes += 1
        self.provider.failures = 0
        if self.provider.circuit == CircuitState.HALF_OPEN:
            if self.provider.successes >= self.provider.success_threshold:
                self.provider.circuit = CircuitState.CLOSED
                self.provider.successes = 0

    def record_failure(self) -> None:
        self.provider.failures += 1
        self.provider.last_failure = time.time()
        if self.provider.circuit == CircuitState.CLOSED:
            if self.provider.failures >= self.provider.failure_threshold:
                self.provider.circuit = CircuitState.OPEN
        elif self.provider.circuit == CircuitState.HALF_OPEN:
            self.provider.circuit = CircuitState.OPEN


@dataclass
class Request:
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    json_body: Optional[Dict[str, Any]] = None

    def transform(self, mapping: Dict[str, Tuple[str, str]]) -> Request:
        headers = dict(self.headers)
        for src, (key, value) in mapping.items():
            if src in headers:
                headers[key] = value
        return Request(
            method=self.method,
            path=self.path,
            headers=headers,
            params=self.params,
            json_body=self.json_body,
        )


@dataclass
class Response:
    status: int
    body: Any
    headers: Dict[str, str] = field(default_factory=dict)


class APIClient:
    def __init__(self, provider: APIProvider) -> None:
        self.provider = provider
        self.breaker = CircuitBreaker(provider)
        self._client: Optional[Callable] = None

    def register_transport(self, transport: Callable) -> None:
        self._client = transport

    def _send(self, request: Request) -> Response:
        if self._client is None:
            raise RuntimeError("No transport registered")
        return self._client(request)

    def request(self, request: Request) -> Response:
        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt <= self.provider.retries:
            if not self.breaker.allow_request():
                raise RuntimeError("Circuit open")
            try:
                response = self._send(request)
                self.breaker.record_success()
                return response
            except Exception as exc:
                last_exc = exc
                self.breaker.record_failure()
                attempt += 1
                if attempt <= self.provider.retries:
                    time.sleep(0.05 * random.uniform(0.8, 1.6) * attempt)
        raise last_exc


class APIGateway:
    def __init__(self) -> None:
        self._providers: Dict[str, APIProvider] = {}
        self._clients: Dict[str, APIClient] = {}
        self._transports: Dict[str, Callable] = {}

    def register_provider(self, provider: APIProvider, transport: Callable) -> None:
        self._providers[provider.name] = provider
        self._transports[provider.name] = transport
        client = APIClient(provider)
        client.register_transport(transport)
        self._clients[provider.name] = client

    def request(self, provider: str, request: Request) -> Response:
        client = self._clients[provider]
        return client.request(request)

    def fan_out(self, requests: Dict[str, Request]) -> Dict[str, Response]:
        return {
            provider: self._clients[provider].request(req)
            for provider, req in requests.items()
        }

    def route_retry(self, provider: str, request: Request) -> Response:
        return self.request(provider, request)
