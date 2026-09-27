import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class HyperparameterLogger:
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self._hyperparameters: Dict[str, Any] = {}
        self._search_space: Dict[str, Any] = {}
        self._best_params: Optional[Dict[str, Any]] = None

    def log_hyperparameters(self, params: Dict[str, Any]) -> None:
        self._hyperparameters.update(params)

    def set_search_space(self, search_space: Dict[str, Any]) -> None:
        self._search_space = search_space

    def set_best_params(self, params: Dict[str, Any], metric_value: float) -> None:
        if self._best_params is None or metric_value > self._best_params.get("metric_value", float("-inf")):
            self._best_params = {
                "params": params,
                "metric_value": metric_value,
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hyperparameters": self._hyperparameters,
            "search_space": self._search_space,
            "best_params": self._best_params,
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))

    @classmethod
    def load(cls, path: Path) -> "HyperparameterLogger":
        data = json.loads(path.read_text())
        logger = cls(data["experiment_id"])
        logger._hyperparameters = data.get("hyperparameters", {})
        logger._search_space = data.get("search_space", {})
        logger._best_params = data.get("best_params")
        return logger
