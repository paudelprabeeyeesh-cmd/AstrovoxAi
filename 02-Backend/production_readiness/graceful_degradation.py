"""Graceful degradation, fallback modes, and circuit breakers."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CircuitBreakerState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    success_threshold: int = 3
    recovery_timeout: float = 30.0
    state: str = field(default=CircuitBreakerState.CLOSED)
    failure_count: int = 0
    success_count: int = 0
    last_failure: float = field(default=0.0)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record_success(self) -> None:
        with self.lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0

    def record_failure(self) -> None:
        now = time.time()
        with self.lock:
            self.failure_count += 1
            self.last_failure = now
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                self.success_count = 0
                return
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN

    def allow_request(self) -> bool:
        now = time.time()
        with self.lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            if self.state == CircuitBreakerState.OPEN:
                if now - self.last_failure >= self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    return True
                return False
            if self.state == CircuitBreakerState.HALF_OPEN:
                return True
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
        }


class FallbackMode:
    CACHE = "cache"
    DEFAULT = "default"
    QUEUE = "queue"
    HUMAN = "human"


class CircuitBreakerRegistry:
    def __init__(self) -> None:
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def register(self, name: str, **kwargs: Any) -> CircuitBreaker:
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name=name, **kwargs)
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        with self._lock:
            return self._breakers.get(name)

    def all(self) -> Dict[str, CircuitBreaker]:
        with self._lock:
            return dict(self._breakers)


class FallbackRegistry:
    def __init__(self) -> None:
        self._fallbacks: Dict[str, Callable[..., Any]] = {}
        self._lock = threading.Lock()

    def register(self, mode: str, func: Callable[..., Any]) -> None:
        with self._lock:
            self._fallbacks[mode] = func

    def get(self, mode: str) -> Optional[Callable[..., Any]]:
        with self._lock:
            return self._fallbacks.get(mode)


class GracefulDegradation:
    def __init__(self) -> None:
        self.breakers = CircuitBreakerRegistry()
        self.fallbacks = FallbackRegistry()
        self._lock = threading.Lock()

    def register_circuit_breaker(self, name: str, **kwargs: Any) -> CircuitBreaker:
        return self.breakers.register(name, **kwargs)

    def register_fallback(self, mode: str, func: Callable[..., Any]) -> None:
        self.fallbacks.register(mode, func)

    def execute_with_degradation(
        self, name: str, func: Callable[..., Any], fallback_mode: str = FallbackMode.DEFAULT, *args: Any, **kwargs: Any
    ) -> Any:
        breaker = self.breakers.get(name)
        if breaker is None:
            breaker = self.register_circuit_breaker(name)
        if not breaker.allow_request():
            fallback = self.fallbacks.get(fallback_mode)
            if fallback is not None:
                logger.info("circuit breaker open, using fallback: %s", name)
                return fallback(*args, **kwargs)
            raise RuntimeError(f"circuit breaker open and no fallback for {name}")
        try:
            result = func(*args, **kwargs)
            breaker.record_success()
            return result
        except Exception as _e:  # noqa: BLE001
            breaker.record_failure()
            raise _e

    def status(self) -> Dict[str, Any]:
        return {name: breaker.to_dict() for name, breaker in self.breakers.all().items()}
