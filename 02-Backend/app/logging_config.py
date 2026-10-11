"""Compatibility shim: delegates to app.core.logging_config.

This module keeps the historical ``app.logging_config`` import path working.
Callers expect three names here: ``configure_logging``, ``get_logger`` and a
module-level ``logger`` created from them.
"""

from app.core.logging_config import (
    configure_logging,
    get_logger,
)

# Historical module-level logger. Kept as an attribute so existing imports
# (`from app.logging_config import logger`) continue to work.
logger = get_logger("astravox")

__all__ = ["configure_logging", "get_logger", "logger"]


_STRUCTLOG_AVAILABLE = False
try:
    import structlog as _sl
    _STRUCTLOG_AVAILABLE = True
except ImportError:
    pass


def get_observability_logger(name: str = "astravox"):
    """Return an observability logger, preferring structlog when installed."""
    if _STRUCTLOG_AVAILABLE:
        return _sl.get_logger(name)
    return get_logger(name)
