"""Chaos engineering experiments."""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ExperimentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ExperimentType(Enum):
    POD_KILL = "pod_kill"
    NETWORK_LATENCY = "network_latency"
    NETWORK_PARTITION = "network_partition"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"
    DISK_FILL = "disk_fill"


@dataclass
class ChaosExperiment:
    experiment_id: str
    name: str
    experiment_type: ExperimentType
    target: str
    duration_seconds: int
    status: ExperimentStatus = ExperimentStatus.PENDING
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ChaosEngine:
    _experiments: Dict[str, ChaosExperiment] = {}

    @classmethod
    def create_experiment(cls, name: str, experiment_type: ExperimentType, target: str, duration_seconds: int, parameters: Optional[Dict[str, Any]] = None) -> ChaosExperiment:
        experiment_id = f"chaos_{datetime.now(timezone.utc).timestamp()}"
        experiment = ChaosExperiment(
            experiment_id=experiment_id,
            name=name,
            experiment_type=experiment_type,
            target=target,
            duration_seconds=duration_seconds,
            parameters=parameters or {},
        )
        cls._experiments[experiment_id] = experiment
        return experiment

    @classmethod
    def start_experiment(cls, experiment_id: str) -> bool:
        experiment = cls._experiments.get(experiment_id)
        if experiment:
            experiment.status = ExperimentStatus.RUNNING
            return True
        return False

    @classmethod
    def stop_experiment(cls, experiment_id: str) -> bool:
        experiment = cls._experiments.get(experiment_id)
        if experiment:
            experiment.status = ExperimentStatus.ROLLED_BACK
            return True
        return False
