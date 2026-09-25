"""Graceful shutdown hook and lifecycle management for FastAPI.

Register `GracefulShutdownMiddleware` to intercept SIGTERM/SIGINT
and drain in-flight requests before the process exits.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Set

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("astrovox.shutdown")

_shutdown_event: asyncio.Event | None = None
_active_requests: Set[asyncio.Task] = set()
_drain_timeout: float = 30.0


class GracefulShutdownMiddleware(BaseHTTPMiddleware):
    """Block new requests once shutdown has started and wait for in-flight requests."""

    def __init__(self, app, drain_timeout: float = 30.0) -> None:
        super().__init__(app)
        self._drain_timeout = drain_timeout
        global _drain_timeout
        _drain_timeout = drain_timeout

    async def dispatch(self, request: Request, call_next):
        if _shutdown_event is not None and _shutdown_event.is_set():
            return JSONResponse(
                status_code=503,
                content={"detail": "Server is shutting down", "code": "SERVER_SHUTTING_DOWN"},
            )
        return await call_next(request)


def get_shutdown_event() -> asyncio.Event | None:
    return _shutdown_event


def get_active_request_count() -> int:
    return len(_active_requests)


def register_lifecycle_handlers(app) -> None:
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()

    def _signal_handler():
        logger.info("Shutdown signal received, draining requests (timeout=%ss)", _drain_timeout)
        _shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows fallback
            signal.signal(sig, lambda s, f: _signal_handler())
