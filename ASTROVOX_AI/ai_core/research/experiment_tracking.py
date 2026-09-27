import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    name: str
    value: float
    step: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ExperimentTracker:
    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self.metrics: List[Metric] = []
        self.params: Dict = {}

    def log_params(self, params: Dict) -> None:
        self.params.update(params)
        logger.info("Logged params for %s", self.experiment_name)

    def log_metric(self, name: str, value: float, step: int) -> None:
        metric = Metric(name=name, value=value, step=step)
        self.metrics.append(metric)
        logger.info("Step %d: %s=%.4f", step, name, value)

    def summary(self) -> Dict:
        return {
            "experiment": self.experiment_name,
            "params": self.params,
            "metrics": [
                {"name": m.name, "value": m.value, "step": m.step, "timestamp": m.timestamp}
                for m in self.metrics
            ],
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tracker = ExperimentTracker("phase9-baseline")
    tracker.log_params({"lr": 1e-3, "batch_size": 32})
    for step in range(1, 4):
        tracker.log_metric("loss", 1.0 / step, step)
    print(tracker.summary())
