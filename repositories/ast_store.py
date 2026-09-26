"""AST store for caching parsed syntax trees."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class ASTStore:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    def get(self, path: str) -> Any | None:
        return self._cache.get(path)

    def put(self, path: str, ast: Any) -> None:
        self._cache[path] = ast

    def invalidate(self, path: str) -> None:
        self._cache.pop(path, None)

    def invalidate_prefix(self, prefix: str) -> None:
        keys = [k for k in self._cache if k.startswith(prefix)]
        for k in keys:
            del self._cache[k]
