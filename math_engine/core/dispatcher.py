"""Topic dispatcher: route topic_id.operation_id to a registered callable."""

from __future__ import annotations

from typing import Any, Callable, Optional

from math_engine.core.result import MathResult
from math_engine.core.errors import UnsupportedTopicError, ValidationError
from math_engine.registry.loader import load_registry, topic_status


class Dispatcher:
    """Dispatch operations to domain modules by topic id."""

    def __init__(self, registry: Optional[dict] = None) -> None:
        self.registry = registry or load_registry()
        self._handlers: dict[str, Callable] = {}
        self._register_builtin_handlers()

    def _register_builtin_handlers(self) -> None:
        # Registered lazily by domain modules to avoid heavy imports.
        pass

    def register(self, topic_id: str, operation_id: str, handler: Callable) -> None:
        self._handlers[f"{topic_id}.{operation_id}"] = handler

    def has(self, topic_id: str, operation_id: str) -> bool:
        return f"{topic_id}.{operation_id}" in self._handlers

    def dispatch(self, topic_id: str, operation_id: str, **kwargs) -> MathResult:
        key = f"{topic_id}.{operation_id}"
        if key not in self._handlers:
            status = topic_status(self.registry, topic_id)
            raise UnsupportedTopicError(
                f"Operation {key} not implemented (registry status: {status})"
            )
        try:
            return self._handlers[key](**kwargs)
        except ValidationError:
            raise
        except Exception as exc:  # noqa: BLE001
            return MathResult(
                topic_id=topic_id,
                operation_id=operation_id,
                status="implemented",
                error=f"{type(exc).__name__}: {exc}",
            )
