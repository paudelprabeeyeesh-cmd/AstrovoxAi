import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_MATH_TASKS = [
    {"id": "m1", "prompt": "What is 2 + 2?", "expected": "4", "type": "arithmetic", "difficulty": "easy"},
    {"id": "m2", "prompt": "What is 15 * 8?", "expected": "120", "type": "arithmetic", "difficulty": "easy"},
    {"id": "m3", "prompt": "Solve for x: 2x + 4 = 10", "expected": "3", "type": "algebra", "difficulty": "medium"},
    {"id": "m4", "prompt": "What is the square root of 144?", "expected": "12", "type": "arithmetic", "difficulty": "easy"},
    {"id": "m5", "prompt": "What is 20% of 50?", "expected": "10", "type": "percentage", "difficulty": "easy"},
    {"id": "m6", "prompt": "If a triangle has angles 90 and 30 degrees, what is the third angle?", "expected": "60", "type": "geometry", "difficulty": "medium"},
    {"id": "m7", "prompt": "What is the derivative of x^2?", "expected": "2x", "type": "calculus", "difficulty": "hard"},
    {"id": "m8", "prompt": "What is 3^4?", "expected": "81", "type": "arithmetic", "difficulty": "easy"},
]


class MathBenchmarks:
    def __init__(self):
        self.tasks = _MATH_TASKS
        self.results: list[dict[str, Any]] = []

    def run_benchmark(self, runner) -> dict[str, Any]:
        passed = 0
        failed = 0
        results = []
        for task in self.tasks:
            try:
                output = runner(task["prompt"])
                expected = str(task.get("expected", "")).strip()
                output_clean = re.sub(r"[^0-9.\-]", "", output.strip())
                score = 1.0 if expected and expected in output_clean else 0.0
                result = {
                    "id": task["id"],
                    "type": task["type"],
                    "difficulty": task.get("difficulty", "unknown"),
                    "prompt": task["prompt"],
                    "output": output,
                    "expected": expected,
                    "score": round(score, 4),
                    "passed": score >= 1.0,
                }
                results.append(result)
                if result["passed"]:
                    passed += 1
                else:
                    failed += 1
            except Exception as exc:  # noqa: BLE001
                results.append({"id": task["id"], "error": str(exc), "passed": False})
                failed += 1
        self.results.extend(results)
        by_difficulty = {}
        for r in results:
            diff = r.get("difficulty", "unknown")
            by_difficulty.setdefault(diff, {"total": 0, "passed": 0})
            by_difficulty[diff]["total"] += 1
            if r.get("passed"):
                by_difficulty[diff]["passed"] += 1
        return {
            "benchmark": "math",
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(results) if results else 0.0,
            "by_difficulty": {k: {"pass_rate": v["passed"] / v["total"] if v["total"] else 0.0} for k, v in by_difficulty.items()},
            "results": results,
        }
