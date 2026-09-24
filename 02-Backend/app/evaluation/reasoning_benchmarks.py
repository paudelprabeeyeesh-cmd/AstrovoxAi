import logging
from typing import Any

logger = logging.getLogger(__name__)

_REASONING_TASKS = [
    {"id": "r1", "type": "deductive", "prompt": "All A are B. All B are C. Therefore, all A are C. Is this valid?", "expected_keywords": ["valid", "yes", "correct", "syllogism"], "difficulty": "easy"},
    {"id": "r2", "type": "inductive", "prompt": "The sun has risen every day. Will it rise tomorrow? Answer yes or no.", "expected_keywords": ["yes"], "difficulty": "easy"},
    {"id": "r3", "type": "abductive", "prompt": "The grass is wet. What is the most likely cause? Rain or fire?", "expected_keywords": ["rain"], "difficulty": "easy"},
    {"id": "r4", "type": "causal", "prompt": "If I drop a glass, it falls. Why?", "expected_keywords": ["gravity"], "difficulty": "easy"},
    {"id": "r5", "type": "commonsense", "prompt": "Can a fish live out of water? Answer yes or no.", "expected_keywords": ["no"], "difficulty": "easy"},
    {"id": "r6", "type": "logical", "prompt": "If it rains, the ground gets wet. It is not wet. Therefore, did it rain? Answer yes or no.", "expected_keywords": ["no", "did not", "didn't"], "difficulty": "medium"},
    {"id": "r7", "type": "multi_step", "prompt": "A bat and a ball cost $1.10. The bat costs $1 more than the ball. How much does the ball cost?", "expected_keywords": ["0.10", "10 cents", "0.1", "ten cents"], "difficulty": "medium"},
    {"id": "r8", "type": "counterfactual", "prompt": "If cars could fly, would we still need roads? Answer with reasoning.", "expected_keywords": ["no", "not", "still"], "difficulty": "medium"},
]


class ReasoningBenchmarks:
    def __init__(self):
        self.tasks = _REASONING_TASKS
        self.results: list[dict[str, Any]] = []

    def run_benchmark(self, runner) -> dict[str, Any]:
        passed = 0
        failed = 0
        results = []
        for task in self.tasks:
            try:
                output = runner(task["prompt"])
                keywords = task.get("expected_keywords", [])
                matched = sum(1 for kw in keywords if kw.lower() in output.lower())
                score = matched / len(keywords) if keywords else 0.0
                result = {
                    "id": task["id"],
                    "type": task["type"],
                    "difficulty": task.get("difficulty", "unknown"),
                    "prompt": task["prompt"],
                    "output": output,
                    "score": round(score, 4),
                    "passed": score >= 0.5,
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
            "benchmark": "reasoning",
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(results) if results else 0.0,
            "by_difficulty": {k: {"pass_rate": v["passed"] / v["total"] if v["total"] else 0.0} for k, v in by_difficulty.items()},
            "results": results,
        }
