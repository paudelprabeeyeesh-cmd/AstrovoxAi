from typing import Dict, Any, List
from dataclasses import dataclass, field
import json


@dataclass
class ResearchRun:
    run_id: str
    model: str
    dataset: str
    metrics: Dict[str, float] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)


class ResearchExperimentTracker:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path

    def save_run(self, run: ResearchRun) -> None:
        with open(f"{self.storage_path}/{run.run_id}.json", "w", encoding="utf-8") as f:
            json.dump(run.__dict__, f, indent=2)

    def load_run(self, run_id: str) -> ResearchRun:
        with open(f"{self.storage_path}/{run_id}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return ResearchRun(**data)
