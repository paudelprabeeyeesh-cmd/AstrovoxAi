import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    experiment_id: str
    name: str
    config: dict[str, Any]
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class Comparison:
    experiment_ids: list[str]
    results: list[dict[str, Any]] = field(default_factory=list)


class ExperimentTracker:
    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}
        self._counter: int = 0

    def start_experiment(self, name: str, config: dict[str, Any] | None = None) -> Experiment:
        self._counter += 1
        experiment = Experiment(experiment_id=f"exp_{self._counter}", name=name, config=config or {})
        self._experiments[experiment.experiment_id] = experiment
        logger.info(f"Started experiment {experiment.experiment_id}: {name}")
        return experiment

    def log_metrics(self, experiment_id: str, metrics: dict[str, float]) -> None:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            logger.error(f"Experiment {experiment_id} not found")
            return
        experiment.metrics.update(metrics)
        logger.info(f"Logged metrics for {experiment_id}: {metrics}")

    def log_parameters(self, experiment_id: str, params: dict[str, Any]) -> None:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            logger.error(f"Experiment {experiment_id} not found")
            return
        experiment.parameters.update(params)
        logger.info(f"Logged parameters for {experiment_id}: {params}")

    def compare_experiments(self, experiment_ids: list[str]) -> Comparison:
        results: list[dict[str, Any]] = []
        for exp_id in experiment_ids:
            experiment = self._experiments.get(exp_id)
            if experiment is None:
                logger.error(f"Experiment {exp_id} not found")
                continue
            results.append({
                "experiment_id": experiment.experiment_id,
                "name": experiment.name,
                "metrics": experiment.metrics,
                "parameters": experiment.parameters,
            })
        return Comparison(experiment_ids=experiment_ids, results=results)
