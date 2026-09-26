"""Automated grading against reference answers and rubrics."""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class GradingResult:
    case_id: str
    passed: bool
    score: float
    max_score: float
    rubric_matches: Dict[str, Any] = field(default_factory=dict)
    feedback: str = ""


class AutomatedGrader:
    def __init__(self, default_max_score: float = 100.0):
        self.default_max_score = default_max_score

    def grade_exact(
        self, case_id: str, answer: str, expected: str, max_score: float = 100.0
    ) -> GradingResult:
        max_score = max_score or self.default_max_score
        passed = answer.strip().lower() == expected.strip().lower()
        score = max_score if passed else 0.0
        return GradingResult(
            case_id=case_id,
            passed=passed,
            score=score,
            max_score=max_score,
            feedback="Exact match" if passed else "Mismatch",
        )

    def grade_regex(
        self, case_id: str, answer: str, pattern: str, max_score: float = 100.0
    ) -> GradingResult:
        max_score = max_score or self.default_max_score
        matched = bool(re.search(pattern, answer, re.IGNORECASE))
        score = max_score if matched else 0.0
        return GradingResult(
            case_id=case_id,
            passed=matched,
            score=score,
            max_score=max_score,
            rubric_matches={"pattern": pattern},
            feedback="Pattern matched" if matched else "Pattern not found",
        )

    def grade_rubric(self, case_id: str, answer: str, rubric: Dict[str, float]) -> GradingResult:
        max_score = sum(rubric.values())
        score = 0.0
        matches = {}
        for criterion, weight in rubric.items():
            if criterion.lower() in answer.lower():
                score += weight
                matches[criterion] = True
            else:
                matches[criterion] = False
        passed = score >= max_score * 0.6
        return GradingResult(
            case_id=case_id,
            passed=passed,
            score=score,
            max_score=max_score,
            rubric_matches=matches,
            feedback="Rubric applied",
        )

    def grade_suite(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for case in cases:
            mode = case.get("mode", "exact")
            if mode == "regex":
                result = self.grade_regex(case["case_id"], case["answer"], case["pattern"])
            elif mode == "rubric":
                result = self.grade_rubric(case["case_id"], case["answer"], case["rubric"])
            else:
                result = self.grade_exact(case["case_id"], case["answer"], case["expected"])
            results.append(result)
        return self._summarize(results)

    def _summarize(self, results: List[GradingResult]) -> Dict[str, Any]:
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total else 0.0,
            "mean_score": sum(r.score for r in results) / total if total else 0.0,
            "max_score": sum(r.max_score for r in results) / total if total else 0.0,
        }

    def get_results(self) -> List[Dict[str, Any]]:
        return [r.__dict__ for r in getattr(self, "_last_results", [])]
