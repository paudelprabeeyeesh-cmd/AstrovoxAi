"""AutoML pipeline scaffolding with train/validation/test orchestration."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class DatasetSplit:
    train: list[Any]
    validation: list[Any]
    test: list[Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineStep:
    name: str
    fn: Callable[..., Any]
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExperimentRun:
    run_id: str
    pipeline_id: str
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0
    status: str = "pending"
    error: str | None = None


class AutoMLPipeline:
    def __init__(self, name: str):
        self.pipeline_id = str(uuid.uuid4())
        self.name = name
        self.steps: list[PipelineStep] = []
        self.runs: list[ExperimentRun] = []
        self._metric_history: list[float] = []

    def add_step(self, name: str, fn: Callable[..., Any], **params: Any) -> AutoMLPipeline:
        self.steps.append(PipelineStep(name=name, fn=fn, params=params))
        return self

    def split_dataset(self, data: list[Any], ratios: tuple[float, float, float] = (0.7, 0.15, 0.15)) -> DatasetSplit:
        train_end = int(len(data) * ratios[0])
        val_end = train_end + int(len(data) * ratios[1])
        return DatasetSplit(
            train=data[:train_end],
            validation=data[train_end:val_end],
            test=data[val_end:],
            metadata={"size": len(data), "ratios": ratios},
        )

    def run(self, dataset: DatasetSplit) -> ExperimentRun:
        run = ExperimentRun(run_id=str(uuid.uuid4()), pipeline_id=self.pipeline_id)
        start = time.perf_counter()
        try:
            artifacts: dict[str, Any] = {"dataset": dataset}
            for step in self.steps:
                artifacts = step.fn(artifacts, **step.params)
            run.artifacts = artifacts
            metric = artifacts.get("metric", 0.0)
            run.metrics = {"primary": float(metric)}
            self._metric_history.append(float(metric))
            run.status = "completed"
        except Exception as exc:
            logger.exception("Pipeline %s failed", self.name)
            run.status = "failed"
            run.error = str(exc)
        run.duration_s = time.perf_counter() - start
        self.runs.append(run)
        return run

    def best_run(self) -> ExperimentRun | None:
        completed = [r for r in self.runs if r.status == "completed"]
        if not completed:
            return None
        return max(completed, key=lambda r: r.metrics.get("primary", -math.inf))
