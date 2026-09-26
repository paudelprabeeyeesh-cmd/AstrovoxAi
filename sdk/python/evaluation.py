from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class EvaluationResult:
    benchmark: str
    score: float
    details: Dict[str, Any]


class EvaluationClient:
    def __init__(self, api_key: str, base_url: str = "https://api.astrovox.ai"):
        self.api_key = api_key
        self.base_url = base_url

    def run_benchmark(self, model_id: str, benchmark_name: str) -> EvaluationResult:
        return EvaluationResult(benchmark=benchmark_name, score=0.0, details={})

    def submit_human_evaluation(self, task_id: str, preference: str, rater_id: str) -> None:
        pass
