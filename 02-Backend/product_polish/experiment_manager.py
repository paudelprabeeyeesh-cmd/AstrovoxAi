"""
experiment_manager - product_polish

Manage A/B experiments with variant assignment and result aggregation.
"""

from __future__ import annotations

import copy
import hashlib
import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExperimentVariant:
    id: str
    name: str
    weight: float = 1.0
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Experiment:
    id: str
    name: str
    variants: List[ExperimentVariant]
    status: str = "draft"
    traffic_allocation: float = 1.0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "variants": [v.to_dict() for v in self.variants],
            "status": self.status,
            "traffic_allocation": self.traffic_allocation,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ExperimentResult:
    experiment_id: str
    variant_id: str
    subject_id: str
    metric: str
    value: float
    recorded_at: str = ""

    def __post_init__(self):
        if not self.recorded_at:
            self.recorded_at = datetime.now(timezone.utc).isoformat()


class ExperimentManager:
    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._results: List[ExperimentResult] = []
        self._lock = threading.Lock()

    def create_experiment(
        self,
        name: str,
        variants: List[Dict[str, Any]],
        status: str = "draft",
        traffic_allocation: float = 1.0,
    ) -> Experiment:
        experiment_id = hashlib.sha256(name.encode() + secrets.token_bytes(8)).hexdigest()[:16]
        variant_objs = [ExperimentVariant(**v) for v in variants]
        experiment = Experiment(
            id=experiment_id,
            name=name,
            variants=variant_objs,
            status=status,
            traffic_allocation=traffic_allocation,
        )
        with self._lock:
            self._experiments[experiment_id] = experiment
        logger.info("Created experiment %s with %d variants", experiment_id, len(variant_objs))
        return experiment

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        with self._lock:
            return self._experiments.get(experiment_id)

    def list_experiments(self) -> List[Experiment]:
        with self._lock:
            return sorted(self._experiments.values(), key=lambda e: e.created_at, reverse=True)

    def assign_variant(self, experiment_id: str, subject_id: str) -> Optional[str]:
        experiment = self.get_experiment(experiment_id)
        if experiment is None or experiment.status != "running":
            return None
        hash_input = f"{experiment_id}:{subject_id}".encode()
        hash_value = int(hashlib.sha256(hash_input).hexdigest(), 16)
        normalized = hash_value % 10000 / 10000
        if normalized > experiment.traffic_allocation:
            return None
        total_weight = sum(v.weight for v in experiment.variants)
        cumulative = 0.0
        remainder = hash_value % 10000
        for variant in experiment.variants:
            cumulative += variant.weight / total_weight
            if remainder / 10000 < cumulative:
                return variant.id
        return experiment.variants[-1].id

    def record_result(
        self, experiment_id: str, variant_id: str, subject_id: str, metric: str, value: float
    ) -> ExperimentResult:
        result = ExperimentResult(
            experiment_id=experiment_id,
            variant_id=variant_id,
            subject_id=subject_id,
            metric=metric,
            value=value,
        )
        with self._lock:
            self._results.append(result)
        logger.info("Recorded result for experiment=%s variant=%s metric=%s", experiment_id, variant_id, metric)
        return result

    def get_results(self, experiment_id: str, metric: Optional[str] = None) -> List[ExperimentResult]:
        with self._lock:
            results = [r for r in self._results if r.experiment_id == experiment_id]
        if metric is not None:
            results = [r for r in results if r.metric == metric]
        return results

    def aggregate_results(self, experiment_id: str, metric: str) -> Dict[str, Dict[str, float]]:
        results = self.get_results(experiment_id, metric)
        by_variant: Dict[str, List[float]] = {}
        for r in results:
            by_variant.setdefault(r.variant_id, []).append(r.value)
        aggregated = {}
        for variant_id, values in by_variant.items():
            if not values:
                continue
            aggregated[variant_id] = {
                "count": len(values),
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
            }
        return aggregated
