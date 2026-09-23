"""Centralized logging configuration.

Call :func:`configure_logging` once at application startup. The log level is
controlled by the ``LOG_LEVEL`` environment variable (default ``INFO``).
"""
import logging
import os

_CONFIGURED = False


def configure_logging() -> None:
    """Configure root logging idempotently."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    _CONFIGURED = True
