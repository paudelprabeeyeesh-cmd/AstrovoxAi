"""Validation helpers for math engine inputs."""

from __future__ import annotations

import math
from typing import Any, Sequence

from math_engine.core.errors import ValidationError, DomainError, PrecisionError


def require_finite(value: Any, name: str) -> float:
    """Coerce to float and require finite."""
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(x):
        raise DomainError(f"{name} must be finite, got {x}")
    return x


def require_non_zero(value: float, name: str) -> float:
    if value == 0.0:
        raise DomainError(f"{name} must be non-zero")
    return value


def require_positive(value: float, name: str) -> float:
    if value <= 0:
        raise DomainError(f"{name} must be positive, got {value}")
    return value


def require_non_negative(value: float, name: str) -> float:
    if value < 0:
        raise DomainError(f"{name} must be non-negative, got {value}")
    return value


def require_shape(data: Sequence[Sequence[Any]], rows: int, cols: int, name: str) -> None:
    if len(data) != rows or any(len(r) != cols for r in data):
        raise ValidationError(f"{name} must have shape ({rows}, {cols})")


def safe_log(x: float, base: float | None = None) -> float:
    if x <= 0:
        raise DomainError("log domain: argument must be positive")
    return math.log(x, base) if base else math.log(x)
