import logging
from typing import Any

logger = logging.getLogger(__name__)


class RegressionTester:
    def __init__(self):
        self.baseline: dict[str, str] = {}

    def set_baseline(self, test_name: str, expected_output: str):
        self.baseline[test_name] = expected_output

    def test(self, test_name: str, actual_output: str) -> dict[str, Any]:
        expected = self.baseline.get(test_name, "")
        passed = actual_output.strip() == expected.strip()
        return {
            "test_name": test_name,
            "passed": passed,
            "expected_length": len(expected),
            "actual_length": len(actual_output),
        }
