import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ExperimentTracker:
    def __init__(self, experiment_dir: str = "experiments"):
        self.experiment_dir = experiment_dir
        os.makedirs(experiment_dir, exist_ok=True)
        self._file = open(os.path.join(experiment_dir, "experiments.jsonl"), "a", encoding="utf-8")

    def log_experiment(self, config: Dict, metrics: Dict, artifacts: Optional[List[str]] = None):
        record = {"config": config, "metrics": metrics, "artifacts": artifacts or []}
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()

    def close(self):
        if self._file:
            self._file.close()


class ScalingProgression:
    def __init__(self, configs: List[str]):
        self.configs = configs
        self.results = []

    def next_config(self, current_metrics: Dict) -> Optional[str]:
        if not self.results:
            return self.configs[0]
        if current_metrics.get("val_loss", float("inf")) < 2.0 and len(self.results) < len(self.configs):
            idx = min(len(self.results), len(self.configs) - 1)
            return self.configs[idx]
        return None

    def record_result(self, config_path: str, metrics: Dict):
        self.results.append({"config": config_path, "metrics": metrics})
