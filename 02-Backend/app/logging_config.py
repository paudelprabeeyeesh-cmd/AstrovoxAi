"""Compatibility shim: delegates to app.core.logging_config."""

from app.core.logging_config import (
    configure_logging,
    get_logger,
)

logger = configure_logging()
_STRUCTLOG_AVAILABLE = False
try:
    import structlog as _sl
    _STRUCTLOG_AVAILABLE = True
except ImportError:
    pass


def get_observability_logger(name: str = "astravox"):
    if _STRUCTLOG_AVAILABLE:
        return _sl.get_logger(name)
    return get_logger(name)
