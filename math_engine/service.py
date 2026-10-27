"""Service layer: thin interface between API routes and the math engine dispatcher."""

from __future__ import annotations

from typing import Any

from math_engine.core.dispatcher import Dispatcher
from math_engine.core.result import MathResult
from math_engine.core.errors import MathEngineError
from math_engine.registry.register import build_dispatcher

_DISPATCHER: Dispatcher | None = None


def get_dispatcher() -> Dispatcher:
    global _DISPATCHER
    if _DISPATCHER is None:
        _DISPATCHER = build_dispatcher()
    return _DISPATCHER


def compute(topic_id: str, operation_id: str, **kwargs) -> dict[str, Any]:
    """Run a math operation and return a plain dict suitable for JSON responses."""
    d = get_dispatcher()
    try:
        res = d.dispatch(topic_id, operation_id, **kwargs)
    except MathEngineError as exc:
        return MathResult(
            topic_id=topic_id, operation_id=operation_id, status="blocked",
            error=str(exc),
        ).to_dict()
    return res.to_dict()


def list_topics() -> dict[str, Any]:
    from math_engine.registry.loader import load_registry
    return load_registry()
