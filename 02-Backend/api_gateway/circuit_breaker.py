import time
import threading
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


@dataclass
class CircuitState:
    state: str = "closed"
    failure_count: int = 0
    last_failure: float = 0.0
    last_success: float = field(default_factory=time.time)
    opened_at: float = 0.0
    half_open_pending: int = 0


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3
    success_threshold: int = 2


class CircuitBreakerOpen(Exception):
    def __init__(self, circuit_name: str, opened_at: float):
        self.circuit_name = circuit_name
        self.opened_at = opened_at
        super().__init__(f"Circuit breaker '{circuit_name}' is open")


class CircuitBreaker:
    def __init__(
        self,
        config: Optional[CircuitBreakerConfig] = None,
        name: str = "default",
    ):
        self._config = config or CircuitBreakerConfig()
        self._name = name
        self._states: Dict[str, CircuitState] = {}
        self._lock = threading.Lock()

    def _get_or_create(self, key: str) -> CircuitState:
        return self._states.setdefault(key, CircuitState())

    def _should_half_open(self, state: CircuitState) -> bool:
        if state.state != "open":
            return False
        return (time.time() - state.opened_at) >= self._config.recovery_timeout

    def _can_half_open_call(self, state: CircuitState) -> bool:
        return (
            state.state == "half_open"
            and state.half_open_pending < self._config.half_open_max_calls
        )

    def allow_request(self, key: str) -> bool:
        with self._lock:
            state = self._get_or_create(key)
            if self._should_half_open(state):
                state.state = "half_open"
                state.half_open_pending = 0
            if state.state == "open":
                return False
            if self._can_half_open_call(state):
                state.half_open_pending += 1
            return True

    def record_success(self, key: str):
        with self._lock:
            state = self._get_or_create(key)
            if state.state == "half_open":
                state.half_open_pending = max(0, state.half_open_pending - 1)
                state.success_count = state.success_count + 1
                if state.success_count >= self._config.success_threshold:
                    state.state = "closed"
                    state.failure_count = 0
                    state.half_open_pending = 0
                    state.success_count = 0
            elif state.state == "closed":
                state.failure_count = 0
            state.last_success = time.time()

    def record_failure(self, key: str):
        with self._lock:
            state = self._get_or_create(key)
            if state.state == "half_open":
                state.half_open_pending = max(0, state.half_open_pending - 1)
                state.state = "open"
                state.opened_at = time.time()
                state.failure_count = 0
                state.success_count = 0
            elif state.state == "closed":
                state.failure_count += 1
                if state.failure_count >= self._config.failure_threshold:
                    state.state = "open"
                    state.opened_at = time.time()
            state.last_failure = time.time()

    def get_state(self, key: str) -> Dict:
        with self._lock:
            state = self._get_or_create(key)
            return {
                "key": key,
                "state": state.state,
                "failure_count": state.failure_count,
                "failure_threshold": self._config.failure_threshold,
                "opened_at": state.opened_at,
                "last_failure": state.last_failure,
                "last_success": state.last_success,
            }

    @property
    def name(self) -> str:
        return self._name

    def reset(self, key: str):
        with self._lock:
            self._states.pop(key, None)

    @property
    def all_states(self) -> Dict[str, Dict]:
        with self._lock:
            return {k: self.get_state(k) for k in self._states}


class CircuitBreakerProxy:
    def __init__(self, breaker: CircuitBreaker, fallback_func=None):
        self._breaker = breaker
        self._fallback_func = fallback_func

    def call(self, key: str, func, *args, **kwargs):
        if not self._breaker.allow_request(key):
            if self._fallback_func:
                return self._fallback_func(key, *args, **kwargs)
            raise CircuitBreakerOpen(self._breaker.name, self._breaker.get_state(key)["opened_at"])
        try:
            result = func(*args, **kwargs)
            self._breaker.record_success(key)
            return result
        except Exception:
            self._breaker.record_failure(key)
            raise
