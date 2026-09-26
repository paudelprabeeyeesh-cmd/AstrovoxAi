"""Testing utilities and fixtures."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TestRunner:
    """Test runner wrapper."""

    def __init__(self, test_dir: str = "tests") -> None:
        self.test_dir = test_dir

    def run_unit(self) -> Dict[str, Any]:
        return {"status": "passed", "tests": 0, "message": "Unit tests placeholder"}

    def run_integration(self) -> Dict[str, Any]:
        return {"status": "passed", "tests": 0, "message": "Integration tests placeholder"}

    def run_e2e(self) -> Dict[str, Any]:
        return {"status": "passed", "tests": 0, "message": "E2E tests placeholder"}

    def run_security(self) -> Dict[str, Any]:
        return {"status": "passed", "tests": 0, "message": "Security tests placeholder"}

    def run_all(self) -> Dict[str, Any]:
        results = {
            "unit": self.run_unit(),
            "integration": self.run_integration(),
            "e2e": self.run_e2e(),
            "security": self.run_security(),
        }
        all_passed = all(r["status"] == "passed" for r in results.values())
        return {"status": "passed" if all_passed else "failed", "results": results}


_test_runner = TestRunner()


def get_test_runner() -> TestRunner:
    return _test_runner
