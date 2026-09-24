import logging
from .prompt_evaluator import PromptEvaluator
from .safety_evaluator import SafetyEvaluator
from .capability_evaluator import CapabilityEvaluator

logger = logging.getLogger(__name__)


class EvalHarness:
    def __init__(self):
        self.prompt_eval = PromptEvaluator()
        self.safety_eval = SafetyEvaluator()
        self.capability_eval = CapabilityEvaluator()
        self.results = []

    def run(self, prompt: str, response: str, reference: str = "") -> dict:
        prompt_result = self.prompt_eval.evaluate(prompt)
        safety_result = self.safety_eval.evaluate(response)
        capability_result = self.capability_eval.evaluate("general", response, reference)

        result = {
            "prompt_scores": prompt_result["scores"],
            "prompt_overall": prompt_result["overall"],
            "safety_scores": safety_result["scores"],
            "safety_overall": safety_result["overall"],
            "capability_scores": capability_result["scores"],
            "capability_overall": capability_result["overall"],
        }
        result["overall"] = round(
            (
                result["prompt_overall"]
                + result["safety_overall"]
                + result["capability_overall"]
            )
            / 3,
            3,
        )
        self.results.append(result)
        return result

    def report(self) -> dict:
        if not self.results:
            return {"count": 0, "avg_overall": 0.0}
        overall_sum = sum(r["overall"] for r in self.results)
        prompt_sum = sum(r["prompt_overall"] for r in self.results)
        safety_sum = sum(r["safety_overall"] for r in self.results)
        capability_sum = sum(r["capability_overall"] for r in self.results)
        n = len(self.results)
        return {
            "count": n,
            "avg_overall": round(overall_sum / n, 3),
            "avg_prompt": round(prompt_sum / n, 3),
            "avg_safety": round(safety_sum / n, 3),
            "avg_capability": round(capability_sum / n, 3),
        }

    def passed(self, threshold: float = 0.5) -> bool:
        report = self.report()
        return report["avg_overall"] >= threshold
