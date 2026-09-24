
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RedTeamCase:
    id: str
    category: str
    prompt: str
    expected_blocked: bool = True
    severity: str = "medium"
    metadata: dict = field(default_factory=dict)


class RedTeamTester:
    def __init__(self):
        self.cases: list[RedTeamCase] = []
        self.results: list[dict[str, Any]] = []

    def register_case(self, case: RedTeamCase) -> None:
        self.cases.append(case)

    def register_cases(self, cases: list[RedTeamCase]) -> None:
        self.cases.extend(cases)

    def run(self, guardrail) -> dict[str, Any]:
        passed = 0
        failed = 0
        results = []
        for case in self.cases:
            blocked = bool(guardrail(case.prompt))
            result = {
                "id": case.id,
                "category": case.category,
                "prompt": case.prompt,
                "expected_blocked": case.expected_blocked,
                "blocked": blocked,
                "passed": blocked == case.expected_blocked,
                "severity": case.severity,
            }
            results.append(result)
            if result["passed"]:
                passed += 1
            else:
                failed += 1
                logger.warning("Red team case failed: %s", case.id)
        self.results.extend(results)
        return {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(results) if results else 0.0,
            "results": results,
        }

    def by_category(self) -> dict[str, dict[str, Any]]:
        summary: dict[str, dict[str, Any]] = {}
        for result in self.results:
            cat = result["category"]
            if cat not in summary:
                summary[cat] = {"total": 0, "passed": 0, "failed": 0}
            summary[cat]["total"] += 1
            if result["passed"]:
                summary[cat]["passed"] += 1
            else:
                summary[cat]["failed"] += 1
        for cat, data in summary.items():
            data["pass_rate"] = data["passed"] / data["total"] if data["total"] else 0.0
        return summary
