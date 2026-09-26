"""Automated grading for open-ended responses."""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Criterion:
    name: str
    description: str
    weight: float = 1.0
    keywords: list[str] = field(default_factory=list)
    regex_patterns: list[str] = field(default_factory=list)


@dataclass
class Rubric:
    id: str
    name: str
    criteria: list[Criterion]
    pass_threshold: float = 0.7


class AutoGrader:
    def __init__(self):
        self._rubrics: dict[str, Rubric] = {}

    def register_rubric(self, rubric: Rubric):
        self._rubrics[rubric.id] = rubric

    def grade(self, response: str, rubric_id: str) -> dict:
        rubric = self._rubrics.get(rubric_id)
        if not rubric:
            raise ValueError(f"Rubric {rubric_id} not found")
        total_score = 0.0
        max_score = sum(c.weight for c in rubric.criteria)
        criteria_results = []
        for criterion in rubric.criteria:
            met, evidence = self._evaluate_criterion(response, criterion)
            score = criterion.weight if met else 0.0
            total_score += score
            criteria_results.append({
                "name": criterion.name,
                "met": met,
                "score": score,
                "weight": criterion.weight,
                "evidence": evidence,
            })
        final_score = total_score / max_score if max_score else 0.0
        return {
            "rubric_id": rubric_id,
            "final_score": round(final_score, 3),
            "passed": final_score >= rubric.pass_threshold,
            "criteria_results": criteria_results,
            "feedback": self._generate_feedback(criteria_results),
        }

    def _evaluate_criterion(self, response: str, criterion: Criterion) -> tuple[bool, str]:
        lowered = response.lower()
        evidence = []
        for kw in criterion.keywords:
            if kw.lower() in lowered:
                evidence.append(f"keyword:{kw}")
        for pattern in criterion.regex_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                evidence.append(f"pattern:{pattern}")
        met = len(evidence) > 0
        return met, "; ".join(evidence) if evidence else "no match"

    def _generate_feedback(self, criteria_results: list[dict]) -> str:
        parts = []
        for cr in criteria_results:
            if cr["met"]:
                parts.append(f"Criterion '{cr['name']}' met.")
            else:
                parts.append(f"Criterion '{cr['name']}' not met.")
        return " ".join(parts)


auto_grader = AutoGrader()
