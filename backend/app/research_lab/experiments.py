from dataclasses import dataclass, field
from typing import Dict, Any, List
import uuid


@dataclass
class ResearchExperiment:
    experiment_id: str
    hypothesis: str
    config: Dict[str, Any]
    results: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "planned"

    def __post_init__(self):
        if not self.experiment_id:
            self.experiment_id = str(uuid.uuid4())


class ResearchLab:
    def __init__(self):
        self.experiments: Dict[str, ResearchExperiment] = {}

    def propose(self, hypothesis: str, config: Dict[str, Any]) -> ResearchExperiment:
        experiment = ResearchExperiment(experiment_id="", hypothesis=hypothesis, config=config)
        self.experiments[experiment.experiment_id] = experiment
        return experiment

    def record_result(self, experiment_id: str, result: Dict[str, Any]) -> None:
        if experiment_id in self.experiments:
            self.experiments[experiment_id].results.append(result)
