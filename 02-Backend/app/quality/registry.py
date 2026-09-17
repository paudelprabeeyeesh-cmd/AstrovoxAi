"""Regression test registry."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RegressionCase:
    bug_id: str
    test_name: str
    module: str


class RegressionTestRegistry:
    def __init__(self) -> None:
        self.registry: dict[str, RegressionCase] = {}

    def register(self, bug_id: str, test_name: str, module: str) -> None:
        self.registry[bug_id] = RegressionCase(bug_id=bug_id, test_name=test_name, module=module)

    def coverage(self) -> dict[str, Any]:
        return {"registered": len(self.registry), "by_module": {}}
