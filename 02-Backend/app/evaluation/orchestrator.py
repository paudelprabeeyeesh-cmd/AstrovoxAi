import logging
from typing import Any, Callable, Optional

from app.evaluation.evaluation_suite import EvaluationSuite
from app.evaluation.red_team import RedTeamTester
from app.evaluation.jailbreak import JailbreakDetector
from app.evaluation.bias_fairness import BiasFairnessEvaluator
from app.evaluation.toxicity import ToxicityEvaluator
from app.evaluation.pii_leakage import PIILeakageTester
from app.evaluation.hallucination import HallucinationDetector
from app.evaluation.alignment import AlignmentTester
from app.evaluation.adversarial import AdversarialTester
from app.evaluation.ab_testing import ABTest, VariantConfig
from app.evaluation.reasoning_benchmarks import ReasoningBenchmarks
from app.evaluation.math_benchmarks import MathBenchmarks
from app.evaluation.coding_benchmarks import CodingBenchmarks
from app.evaluation.multi_turn_eval import MultiTurnEvaluator
from app.evaluation.tool_use_eval import ToolUseEvaluator
from app.evaluation.retrieval_benchmark import RetrievalBenchmark
from app.evaluation.end_to_end_pipeline import EndToEndEvaluationPipeline
from app.evaluation.continuous_eval import ContinuousEvaluator

logger = logging.getLogger(__name__)


class EvaluationOrchestrator:
    def __init__(self):
        self.suite = EvaluationSuite()
        self.red_team = RedTeamTester()
        self.jailbreak = JailbreakDetector()
        self.bias = BiasFairnessEvaluator()
        self.toxicity = ToxicityEvaluator()
        self.pii = PIILeakageTester()
        self.hallucination = HallucinationDetector()
        self.alignment = AlignmentTester()
        self.adversarial = AdversarialTester()
        self.reasoning = ReasoningBenchmarks()
        self.math = MathBenchmarks()
        self.coding = CodingBenchmarks()
        self.multi_turn = MultiTurnEvaluator()
        self.tool_use = ToolUseEvaluator()
        self.retrieval = RetrievalBenchmark()
        self.pipeline = EndToEndEvaluationPipeline()
        self.continuous: Optional[ContinuousEvaluator] = None

    def run_safety_eval(self, text: str) -> dict[str, Any]:
        jailbreak_result = self.jailbreak.detect(text)
        toxicity_result = self.toxicity.evaluate(text)
        pii_result = self.pii.test(text)
        return {
            "jailbreak": jailbreak_result,
            "toxicity": toxicity_result,
            "pii": pii_result,
            "overall_safe": not jailbreak_result["blocked"] and toxicity_result["score"] >= 0.7 and not pii_result["leaked"],
        }

    def run_capability_eval(self, response: str, reference: str = "") -> dict[str, Any]:
        from app.evaluation.metrics import MetricsCalculator
        calc = MetricsCalculator()
        metrics = calc.calculate(response, "", reference)
        return metrics

    def run_full_eval(self, prompt: str, response: str, reference: str = "", context: str = "") -> dict[str, Any]:
        safety = self.run_safety_eval(response)
        capability = self.run_capability_eval(response, reference)
        hallucination = self.hallucination.detect(response, context)
        alignment = self.alignment.evaluate(response)
        return {
            "prompt": prompt,
            "safety": safety,
            "capability": capability,
            "hallucination": hallucination,
            "alignment": alignment,
        }

    def run_benchmark_suite(self, runner: Callable[[str], str]) -> dict[str, Any]:
        reasoning = self.reasoning.run_benchmark(runner)
        math = self.math.run_benchmark(runner)
        coding = self.coding.run_benchmark(runner)
        return {
            "reasoning": reasoning,
            "math": math,
            "coding": coding,
        }

    def run_retrieval_eval(self, queries: list[dict[str, Any]], ground_truth: dict[str, list[str]]) -> dict[str, Any]:
        result = self.retrieval.run_benchmark(queries, ground_truth)
        return result.generate_report()

    def start_continuous_eval(self, evaluation_fn: Callable[[], dict[str, Any]], interval_seconds: float = 3600.0) -> ContinuousEvaluator:
        self.continuous = ContinuousEvaluator(evaluation_fn, interval_seconds)
        self.continuous.start()
        return self.continuous
