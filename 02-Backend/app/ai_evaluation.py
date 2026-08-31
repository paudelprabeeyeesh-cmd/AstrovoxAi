"""AI Evaluation — prompt versioning, quality scoring, benchmarks."""

import time
import json
import logging
import secrets
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class PromptVersion:
    """A version of a prompt."""
    id: str
    name: str
    content: str
    version: int
    created_at: float
    is_active: bool = True
    metadata: dict = field(default_factory=dict)


@dataclass
class EvaluationResult:
    """Result of an AI evaluation."""
    id: str
    prompt_name: str
    prompt_version: int
    model: str
    response: str
    quality_score: float
    latency_ms: float
    token_count: int
    timestamp: float
    metrics: dict = field(default_factory=dict)


@dataclass
class BenchmarkCase:
    """A benchmark test case."""
    id: str
    name: str
    category: str
    input: str
    expected_output: str
    evaluation_criteria: list[str]


class PromptManager:
    """Manage prompt versions and A/B testing."""

    def __init__(self):
        self._prompts: dict[str, list[PromptVersion]] = {}
        self._active_prompts: dict[str, PromptVersion] = {}

    def create_prompt(self, name: str, content: str, metadata: dict = None) -> PromptVersion:
        """Create a new prompt version."""
        versions = self._prompts.get(name, [])
        version_num = len(versions) + 1

        prompt = PromptVersion(
            id=secrets.token_hex(8),
            name=name,
            content=content,
            version=version_num,
            created_at=time.time(),
            metadata=metadata or {},
        )

        versions.append(prompt)
        self._prompts[name] = versions
        self._active_prompts[name] = prompt

        return prompt

    def get_active_prompt(self, name: str) -> Optional[PromptVersion]:
        """Get the active version of a prompt."""
        return self._active_prompts.get(name)

    def get_prompt_versions(self, name: str) -> list[PromptVersion]:
        """Get all versions of a prompt."""
        return self._prompts.get(name, [])

    def set_active_version(self, name: str, version: int) -> bool:
        """Set the active version of a prompt."""
        versions = self._prompts.get(name, [])
        for v in versions:
            if v.version == version:
                v.is_active = True
                self._active_prompts[name] = v
                for other in versions:
                    if other.version != version:
                        other.is_active = False
                return True
        return False

    def compare_versions(self, name: str, v1: int, v2: int) -> dict:
        """Compare two prompt versions."""
        versions = self._prompts.get(name, [])
        p1 = next((p for p in versions if p.version == v1), None)
        p2 = next((p for p in versions if p.version == v2), None)

        if not p1 or not p2:
            return {"error": "Version not found"}

        return {
            "version_1": {"version": p1.version, "content": p1.content},
            "version_2": {"version": p2.version, "content": p2.content},
            "differences": self._compute_diff(p1.content, p2.content),
        }

    def _compute_diff(self, text1: str, text2: str) -> list[str]:
        """Compute differences between two texts."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        added = words2 - words1
        removed = words1 - words2
        return [f"+ {w}" for w in added] + [f"- {w}" for w in removed]


class QualityScorer:
    """Score AI response quality."""

    def score_response(
        self,
        response: str,
        expected: str = "",
        criteria: list[str] = None,
    ) -> dict:
        """Score a response on multiple criteria."""
        scores = {}

        scores["length"] = min(len(response) / 500, 1.0)

        sentences = response.split(".")
        scores["coherence"] = min(len(sentences) / 5, 1.0)

        if expected:
            expected_words = set(expected.lower().split())
            response_words = set(response.lower().split())
            overlap = len(expected_words & response_words)
            scores["relevance"] = overlap / max(len(expected_words), 1)
        else:
            scores["relevance"] = 0.5

        scores["completeness"] = min(len(response.split()) / 100, 1.0)

        overall = sum(scores.values()) / len(scores) if scores else 0

        return {
            "overall_score": round(overall, 3),
            "criteria_scores": scores,
            "grade": self._score_to_grade(overall),
        }

    def _score_to_grade(self, score: float) -> str:
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"


class BenchmarkSuite:
    """AI model benchmarking suite."""

    def __init__(self):
        self._cases: list[BenchmarkCase] = []
        self._results: list[EvaluationResult] = []
        self._setup_default_cases()

    def _setup_default_cases(self):
        """Setup default benchmark cases."""
        self._cases = [
            BenchmarkCase(
                id="summarization_1",
                name="Text Summarization",
                category="summarization",
                input="Summarize: Machine learning is a subset of AI...",
                expected_output="Machine learning enables systems to learn from data.",
                evaluation_criteria=["accuracy", "conciseness"],
            ),
            BenchmarkCase(
                id="code_gen_1",
                name="Code Generation",
                category="code",
                input="Write a Python function to sort a list.",
                expected_output="def sort_list(lst): return sorted(lst)",
                evaluation_criteria=["correctness", "efficiency"],
            ),
            BenchmarkCase(
                id="qa_1",
                name="Question Answering",
                category="qa",
                input="What is the capital of France?",
                expected_output="Paris",
                evaluation_criteria=["accuracy"],
            ),
        ]

    def add_case(self, case: BenchmarkCase):
        """Add a benchmark case."""
        self._cases.append(case)

    def get_cases(self, category: str = None) -> list[BenchmarkCase]:
        """Get benchmark cases."""
        if category:
            return [c for c in self._cases if c.category == category]
        return self._cases

    def record_result(self, result: EvaluationResult):
        """Record an evaluation result."""
        self._results.append(result)

    def get_results(
        self,
        model: str = None,
        prompt_name: str = None,
    ) -> list[EvaluationResult]:
        """Get evaluation results."""
        results = self._results
        if model:
            results = [r for r in results if r.model == model]
        if prompt_name:
            results = [r for r in results if r.prompt_name == prompt_name]
        return results

    def get_model_comparison(self) -> dict:
        """Compare models across benchmarks."""
        model_scores = defaultdict(lambda: {"scores": [], "avg_score": 0})

        for result in self._results:
            model_scores[result.model]["scores"].append(result.quality_score)

        for model, data in model_scores.items():
            if data["scores"]:
                data["avg_score"] = round(sum(data["scores"]) / len(data["scores"]), 3)

        return dict(model_scores)

    def get_benchmark_report(self) -> dict:
        """Generate a benchmark report."""
        return {
            "total_cases": len(self._cases),
            "total_evaluations": len(self._results),
            "model_comparison": self.get_model_comparison(),
            "categories": list(set(c.category for c in self._cases)),
        }


prompt_manager = PromptManager()
quality_scorer = QualityScorer()
benchmark_suite = BenchmarkSuite()
