"""Structured errors for the math engine."""

from __future__ import annotations


class MathEngineError(Exception):
    """Base error for math engine operations."""


class DomainError(MathEngineError):
    """Input outside the mathematical domain (e.g. log of negative)."""


class PrecisionError(MathEngineError):
    """Numerical precision limit reached."""


class ValidationError(MathEngineError):
    """Malformed input or invalid shape."""


class UnsupportedTopicError(MathEngineError):
    """Requested topic/operation is not implemented."""


class ResourceLimitError(MathEngineError):
    """Request exceeds execution limits (size, time, iterations)."""
