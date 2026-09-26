"""Regression testing framework."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RegressionTestCase:
    test_id: str
    name: str
    baseline: Any
    func: Callable[[], Any]
    tolerance: float = 0.01


class RegressionTestSuite:
    def __init__(self) -> None:
        self._cases: List[RegressionTestCase] = []

    def add_case(self, case: RegressionTestCase) -> None:
        self._cases.append(case)

    def run(self) -> Dict[str, Any]:
        passed = 0
        for case in self._cases:
            try:
                result = case.func()
                if isinstance(case.baseline, (int, float)) and isinstance(result, (int, float)):
                    if abs(result - case.baseline) <= case.tolerance:
                        passed += 1
                elif result == case.baseline:
                    passed += 1
            except Exception:
                pass
        return {"passed": passed, "total": len(self._cases)}


regression_test_suite = RegressionTestSuite()
