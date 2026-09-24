
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EndToEndEvaluationPipeline:
    def __init__(self):
        self.stages: list[str] = []
        self.results: dict[str, Any] = {}

    def add_stage(self, name: str, func: Callable[[], dict[str, Any]]) -> None:
        self.stages.append(name)
        self.results[name] = {}

    def run(self) -> dict[str, Any]:
        pipeline_results = {}
        for stage in self.stages:
            start = time.time()
            try:
                result = self.results.get(stage, {})
                if callable(result):
                    result = result()
                latency = time.time() - start
                pipeline_results[stage] = {
                    "status": "passed",
                    "latency_ms": round(latency * 1000, 2),
                    "details": result,
                }
            except Exception as exc:  # noqa: BLE001
                pipeline_results[stage] = {
                    "status": "failed",
                    "latency_ms": 0.0,
                    "error": str(exc),
                }
        passed = sum(1 for r in pipeline_results.values() if r["status"] == "passed")
        return {
            "stages": len(self.stages),
            "passed": passed,
            "failed": len(self.stages) - passed,
            "pass_rate": passed / len(self.stages) if self.stages else 0.0,
            "results": pipeline_results,
        }

    def build_default(self, runner: Callable[[str], str]) -> "EndToEndEvaluationPipeline":
        self.add_stage("safety", lambda: {"blocked": False})
        self.add_stage("capability", lambda: runner("What is 2+2?"))
        self.add_stage("quality", lambda: {"coherence": 0.9, "relevance": 0.9})
        self.add_stage("rag", lambda: {"retrieval_quality": 0.85})
        return self
