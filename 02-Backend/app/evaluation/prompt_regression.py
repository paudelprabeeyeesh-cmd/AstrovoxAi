import logging
from typing import Any

logger = logging.getLogger(__name__)


class PromptRegressionTester:
    def __init__(self):
        self.tests: dict[str, list[dict]] = {}

    def test_prompt(self, prompt_name: str, test_cases: list[dict]) -> dict[str, Any]:
        results = []
        for case in test_cases:
            input_text = case.get("input", "")
            expected = case.get("expected", "")
            passed = input_text == expected
            results.append({
                "input": input_text,
                "expected": expected,
                "passed": passed,
            })
        self.tests[prompt_name] = results
        return {
            "prompt_name": prompt_name,
            "total": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "results": results,
        }

    def compare_versions(self, prompt_name: str, v1: str, v2: str, test_cases: list[dict]) -> dict[str, Any]:
        v1_results = self.test_prompt(f"{prompt_name}_v1", test_cases)
        v2_results = self.test_prompt(f"{prompt_name}_v2", test_cases)
        return {
            "prompt_name": prompt_name,
            "v1": v1_results,
            "v2": v2_results,
            "v1_pass_rate": v1_results["passed"] / max(v1_results["total"], 1),
            "v2_pass_rate": v2_results["passed"] / max(v2_results["total"], 1),
        }
