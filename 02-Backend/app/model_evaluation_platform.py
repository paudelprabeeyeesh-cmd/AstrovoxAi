"""Model evaluation platform."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EvaluationSuite:
    suite_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    benchmarks: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class EvaluationRun:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    suite_id: str = ""
    model_id: str = ""
    model_version: str = ""
    status: EvaluationStatus = EvaluationStatus.PENDING
    results: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None


class ModelEvaluationPlatform:
    """Model evaluation and benchmarking platform."""

    def __init__(self):
        self._suites: Dict[str, EvaluationSuite] = {}
        self._runs: Dict[str, EvaluationRun] = {}

    def create_suite(self, name: str, benchmarks: List[str], metrics: List[str]) -> EvaluationSuite:
        suite = EvaluationSuite(name=name, benchmarks=benchmarks, metrics=metrics)
        self._suites[suite.suite_id] = suite
        logger.info("Created evaluation suite: %s", name)
        return suite

    def start_evaluation(self, suite_id: str, model_id: str, model_version: str) -> Optional[EvaluationRun]:
        suite = self._suites.get(suite_id)
        if not suite:
            return None
        run = EvaluationRun(suite_id=suite_id, model_id=model_id, model_version=model_version, status=EvaluationStatus.RUNNING, started_at=time.time())
        self._runs[run.run_id] = run
        logger.info("Started evaluation run %s for model %s:%s", run.run_id, model_id, model_version)
        return run

    def complete_evaluation(self, run_id: str, results: Dict[str, Any]) -> bool:
        run = self._runs.get(run_id)
        if not run:
            return False
        run.status = EvaluationStatus.COMPLETED
        run.results = results
        run.completed_at = time.time()
        logger.info("Completed evaluation run %s", run_id)
        return True

    def fail_evaluation(self, run_id: str, error: str) -> bool:
        run = self._runs.get(run_id)
        if not run:
            return False
        run.status = EvaluationStatus.FAILED
        run.error = error
        run.completed_at = time.time()
        return True

    def get_run(self, run_id: str) -> Optional[EvaluationRun]:
        return self._runs.get(run_id)

    def get_model_history(self, model_id: str) -> List[EvaluationRun]:
        return [r for r in self._runs.values() if r.model_id == model_id]

    def compare_models(self, model_ids: List[str], metric: str = "accuracy") -> Dict[str, Any]:
        comparison = {}
        for model_id in model_ids:
            runs = [r for r in self._runs.values() if r.model_id == model_id and r.status == EvaluationStatus.COMPLETED]
            if not runs:
                continue
            scores = [r.results.get(metric, 0.0) for r in runs if metric in r.results]
            if scores:
                comparison[model_id] = {"avg": round(sum(scores) / len(scores), 4), "count": len(scores), "best": round(max(scores), 4)}
        return comparison


model_evaluation_platform = ModelEvaluationPlatform()
