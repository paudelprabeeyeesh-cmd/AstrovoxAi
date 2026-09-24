
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_CODING_TASKS = [
    {"id": "c1", "prompt": "Write a Python function that returns the sum of two numbers.", "expected_keywords": ["def", "return", "+"], "language": "python"},
    {"id": "c2", "prompt": "Write a function to check if a string is a palindrome.", "expected_keywords": ["def", "return", "==", "reverse"], "language": "python"},
    {"id": "c3", "prompt": "Implement a binary search algorithm.", "expected_keywords": ["def", "mid", "return", "while"], "language": "python"},
    {"id": "c4", "prompt": "Write a function to sort a list of numbers.", "expected_keywords": ["def", "return", "sort", "sorted"], "language": "python"},
    {"id": "c5", "prompt": "Write a function to reverse a linked list.", "expected_keywords": ["def", "next", "prev", "return"], "language": "python"},
]


class CodingBenchmarks:
    def __init__(self):
        self.tasks = _CODING_TASKS
        self.results: list[dict[str, Any]] = []

    def run_benchmark(self, runner) -> dict[str, Any]:
        passed = 0
        failed = 0
        results = []
        for task in self.tasks:
            try:
                output = runner(task["prompt"])
                keywords = task.get("expected_keywords", [])
                output_lower = output.lower()
                matched = sum(1 for kw in keywords if kw.lower() in output_lower)
                score = matched / len(keywords) if keywords else 0.0
                result = {
                    "id": task["id"],
                    "language": task.get("language", "unknown"),
                    "prompt": task["prompt"],
                    "output": output,
                    "score": round(score, 4),
                    "passed": score >= 0.6,
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
        return {
            "benchmark": "coding",
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(results) if results else 0.0,
            "results": results,
        }
