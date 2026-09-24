"""Ordered startup sequence with hooks."""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class StartupSequence:
    def __init__(self) -> None:
        self._steps: List[Tuple[str, Callable[[], Dict[str, Any]]]] = []
        self._completed: List[str] = []
        self._failed: List[str] = []

    def add_step(self, name: str, step: Callable[[], Dict[str, Any]]) -> None:
        self._steps.append((name, step))

    def run(self) -> Tuple[bool, List[str], List[str]]:
        self._completed = []
        self._failed = []
        for name, step in self._steps:
            logger.info("startup step: %s", name)
            try:
                step()
                self._completed.append(name)
            except Exception as exc:  # noqa: BLE001
                logger.error("startup step failed %s -> %s", name, exc)
                self._failed.append(name)
        return len(self._failed) == 0, list(self._completed), list(self._failed)
