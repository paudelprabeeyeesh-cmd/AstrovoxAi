"""Graceful shutdown with coordinated in-flight request draining."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GracefulShutdown:
    def __init__(self, drain_timeout: float = 30.0) -> None:
        self._drain_timeout = drain_timeout
        self._is_shutting_down: bool = False
        self._is_draining: bool = False
        self._is_up: bool = True
        self._lock: threading.Lock = threading.Lock()
        self._active: threading.Semaphore = threading.Semaphore(1)
        self._on_exit: Optional[Callable[[], None]] = None

    def register_exit(self, on_exit: Callable[[], None]) -> None:
        self._on_exit = on_exit

    def shutdown(self) -> None:
        if not self._is_up:
            return
        with self._lock:
            if self._is_shutting_down:
                return
            self._is_shutting_down = True
            self._is_draining = True
            self._is_up = False
        logger.info("shutdown initiated")

    def drain(self) -> None:
        if not self._is_up:
            return
        self.shutdown()
        logger.info("draining in-flight requests")
        waited = 0.0
        while self._active.acquire(timeout=0.1):
            waited += 0.1
            if waited >= self._drain_timeout:
                logger.warning("drain timeout reached; proceeding")
                break
        logger.info("drain complete")

    def stop(self) -> None:
        self.drain()
        logger.info("stopping now")
        if self._on_exit:
            try:
                self._on_exit()
            except Exception as exc:  # noqa: BLE001
                logger.error("exit handler failed: %s", exc)

    def is_shutting_down(self) -> bool:
        return self._is_shutting_down

    def is_draining(self) -> bool:
        return self._is_draining

    def is_up(self) -> bool:
        return self._is_up
