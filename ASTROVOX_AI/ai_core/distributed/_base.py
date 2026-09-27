"""Shared base classes and utilities for distributed subsystems."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


class BackgroundService:
    """Base class for background services with start/stop lifecycle."""

    def __init__(self, check_interval: float = 15.0) -> None:
        self.check_interval = check_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("%s started", self.__class__.__name__)

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("%s stopped", self.__class__.__name__)

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception:
                logger.exception("%s error", self.__class__.__name__)
            time.sleep(self.check_interval)

    def _tick(self) -> None:
        raise NotImplementedError


def validate_node_id(node_id: str) -> None:
    if not node_id or not isinstance(node_id, str):
        raise ValueError("node_id must be a non-empty string")


def validate_positive_float(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_non_negative_int(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")
