"""Dependency ownership tracking."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DependencyOwnership:
    def __init__(self) -> None:
        self.owners: dict[str, str] = {}

    def assign(self, package: str, owner: str) -> None:
        self.owners[package] = owner

    def status(self) -> dict[str, Any]:
        return {"total_dependencies": len(self.owners), "unowned": [p for p, owner in self.owners.items() if not owner]}
