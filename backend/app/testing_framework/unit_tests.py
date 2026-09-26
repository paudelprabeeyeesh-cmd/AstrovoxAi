"""Unit testing framework."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UnitTestCase:
    test_id: str
    name: str
    func: Callable[[], Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnitTestSuite:
    suite_id: str
    name: str
    cases: List[UnitTestCase] = field(default_factory=list)


class UnitTestRunner:
    def __init__(self) -> None:
        self._suites: Dict[str, UnitTestSuite] = {}

    def register_suite(self, suite: UnitTestSuite) -> None:
        self._suites[suite.suite_id] = suite

    def run(self, suite_id: str) -> Dict[str, Any]:
        suite = self._suites.get(suite_id)
        if not suite:
            raise ValueError(f"Unknown suite: {suite_id}")
        passed = sum(1 for case in suite.cases if self._run_case(case))
        return {"suite_id": suite_id, "passed": passed, "total": len(suite.cases)}

    def _run_case(self, case: UnitTestCase) -> bool:
        try:
            result = case.func()
            return result is None or result is True
        except Exception:
            return False


unit_test_runner = UnitTestRunner()
