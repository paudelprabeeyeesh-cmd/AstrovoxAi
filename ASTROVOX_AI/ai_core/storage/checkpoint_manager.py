import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Checkpoint:
    checkpoint_id: str
    model_name: str
    epoch: int
    step: int
    metrics: dict = field(default_factory=dict)
    path: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class CheckpointManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def save(self, checkpoint: Checkpoint) -> str:
        path = os.path.join(self.base_dir, f"{checkpoint.checkpoint_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(checkpoint), f, indent=2)
        checkpoint.path = path
        return path

    def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        path = os.path.join(self.base_dir, f"{checkpoint_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Checkpoint(**data)

    def list_checkpoints(self, model_name: Optional[str] = None) -> list:
        checkpoints = []
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                checkpoint = self.load(filename[:-5])
                if checkpoint and (model_name is None or checkpoint.model_name == model_name):
                    checkpoints.append(checkpoint)
        return sorted(checkpoints, key=lambda c: c.created_at)
