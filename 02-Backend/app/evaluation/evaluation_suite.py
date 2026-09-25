import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EvaluationSuite:
    def __init__(self):
        self.suites = {}

    def register_suite(self, name: str, cases: list[dict]):
        self.suites[name] = cases

    def run_suite(self, name: str, runner) -> dict[str, Any]:
        cases = self.suites.get(name, [])
        results = []
        passed = 0
        failed = 0
        total_latency = 0.0
        for case in cases:
            prompt = case.get("prompt", "")
            expected = case.get("expected", "")
            rubric = case.get("rubric", {})
            start = time.time()
            try:
                output = runner(prompt)
                latency = time.time() - start
                score = self._score_output(output, expected, rubric)
                result = {
                    "prompt": prompt,
                    "expected": expected,
                    "output": output,
                    "score": score,
                    "latency_ms": round(latency * 1000, 2),
                    "passed": score >= rubric.get("pass_threshold", 0.7),
                }
                results.append(result)
                if result["passed"]:
                    passed += 1
                else:
                    failed += 1
                total_latency += latency
            except Exception as e:
                failed += 1
                results.append({
                    "prompt": prompt,
                    "expected": expected,
                    "output": "",
                    "score": 0.0,
                    "latency_ms": 0,
                    "passed": False,
                    "error": str(e),
                })
        return {
            "suite": name,
            "total": len(cases),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(cases) if cases else 0.0,
            "avg_latency_ms": round((total_latency / len(cases)) * 1000, 2) if cases else 0.0,
            "results": results,
        }

    def _score_output(self, output: str, expected: str, rubric: dict) -> float:
        if not output:
            return 0.0
        score = 0.5
        if expected:
            output_lower = output.lower()
            expected_lower = expected.lower()
            if expected_lower in output_lower:
                score += 0.3
            words = set(expected_lower.split())
            overlap = len([w for w in words if w in output_lower and len(w) > 3])
            if words:
                score += 0.2 * (overlap / len(words))
        return min(1.0, max(0.0, score))
