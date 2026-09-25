import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    model_id: str
    dataset_name: str
    metrics: dict[str, float]
    passed: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Comparison:
    model_ids: list[str]
    results: list[EvaluationResult] = field(default_factory=list)
    best_model_id: str | None = None


@dataclass
class DeploymentStatus:
    model_id: str
    traffic_percentage: float
    active: bool
    metrics: dict[str, float] = field(default_factory=dict)
    rolled_back: bool = False


class EvaluationPipeline:
    def __init__(self, model_registry: Any, dataset_registry: Any) -> None:
        self.model_registry = model_registry
        self.dataset_registry = dataset_registry

    def evaluate_model(self, model_id: str, test_dataset: Any) -> EvaluationResult:
        metrics: dict[str, float] = {}
        passed = True
        details: dict[str, Any] = {}

        model = self.model_registry.get_model(model_id, "")
        if model is None:
            passed = False
            details["error"] = "Model not found"
        else:
            metrics["accuracy"] = 0.0
            metrics["latency_ms"] = 0.0

        result = EvaluationResult(model_id=model_id, dataset_name=str(test_dataset), metrics=metrics, passed=passed, details=details)
        logger.info(f"Evaluated model {model_id}: passed={passed}")
        return result

    def compare_models(self, model_ids: list[str], test_dataset: Any) -> Comparison:
        results: list[EvaluationResult] = []
        for model_id in model_ids:
            results.append(self.evaluate_model(model_id, test_dataset))
        best_model_id = None
        if results:
            best_model_id = max(results, key=lambda r: r.metrics.get("accuracy", 0.0)).model_id
        return Comparison(model_ids=model_ids, results=results, best_model_id=best_model_id)

    def canary_deployment(self, model_id: str, traffic_percentage: float) -> DeploymentStatus:
        status = DeploymentStatus(model_id=model_id, traffic_percentage=traffic_percentage, active=True)
        logger.info(f"Started canary deployment for model {model_id} at {traffic_percentage}% traffic")
        return status
