"""Evaluation lab for running experiments and comparing models."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    id: str
    name: str
    config: dict
    metrics: dict = field(default_factory=dict)
    status: str = "created"


class EvaluationLab:
    def __init__(self):
        self._experiments: dict[str, Experiment] = {}

    def create_experiment(self, name: str, config: dict) -> Experiment:
        experiment_id = str(uuid.uuid4())
        experiment = Experiment(id=experiment_id, name=name, config=config)
        self._experiments[experiment_id] = experiment
        self._persist(experiment)
        return experiment

    def _persist(self, experiment: Experiment):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO evaluation_experiments (id, name, config, metrics, status) VALUES (?, ?, ?, ?, ?)",
                (experiment.id, experiment.name, json.dumps(experiment.config), json.dumps(experiment.metrics), experiment.status),
            )
            conn.commit()

    def run(self, experiment_id: str, dataset: list[dict], model_func) -> dict:
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        experiment.status = "running"
        self._persist(experiment)
        results = []
        for item in dataset:
            try:
                output = model_func(item.get("prompt", ""))
                results.append({"prompt": item.get("prompt"), "output": output})
            except Exception as exc:
                results.append({"prompt": item.get("prompt"), "error": str(exc)})
        experiment.metrics = {"total": len(results), "errors": sum(1 for r in results if "error" in r)}
        experiment.status = "completed"
        self._persist(experiment)
        return {"experiment_id": experiment.id, "results": results, "metrics": experiment.metrics}

    def compare(self, experiment_ids: list[str]) -> dict:
        comparison = {}
        for eid in experiment_ids:
            exp = self._experiments.get(eid)
            if exp:
                comparison[eid] = {"name": exp.name, "status": exp.status, "metrics": exp.metrics}
        return comparison


import json

evaluation_lab = EvaluationLab()
