import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List
from datetime import datetime


@dataclass
class Experiment:
    experiment_id: str
    name: str
    params: Dict[str, Any]
    metrics: Dict[str, float] = field(default_factory=dict)
    status: str = "running"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ExperimentTracker:
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}

    def create_experiment(self, name: str, params: Dict[str, Any]) -> Experiment:
        experiment = Experiment(experiment_id=str(uuid.uuid4()), name=name, params=params)
        self.experiments[experiment.experiment_id] = experiment
        return experiment

    def log_metric(self, experiment_id: str, key: str, value: float) -> None:
        if experiment_id in self.experiments:
            self.experiments[experiment_id].metrics[key] = value

    def complete(self, experiment_id: str) -> None:
        if experiment_id in self.experiments:
            self.experiments[experiment_id].status = "completed"
