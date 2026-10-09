import json
import os
from typing import Any, Dict, Optional, Tuple


class CheckpointManager:
    def __init__(self, directory: str = "checkpoints") -> None:
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def save(self, step: int, state: Dict[str, Any]) -> str:
        path = os.path.join(self.directory, f"ckpt_{step}.json")
        payload = {"step": step, "state": state}
        tmp_path = path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(payload, f)
        os.replace(tmp_path, path)
        meta_path = os.path.join(self.directory, f"ckpt_{step}.meta.json")
        with open(meta_path, "w") as f:
            json.dump({"step": step, "path": path}, f)
        return path

    def load(self, step: int) -> Tuple[int, Dict[str, Any]]:
        path = os.path.join(self.directory, f"ckpt_{step}.json")
        with open(path, "r") as f:
            payload = json.load(f)
        return int(payload["step"]), dict(payload["state"])

    def latest(self) -> Optional[int]:
        steps = []
        for name in os.listdir(self.directory):
            if name.startswith("ckpt_") and name.endswith(".json") and ".meta" not in name:
                try:
                    steps.append(int(name.replace("ckpt_", "").replace(".json", "")))
                except ValueError:
                    continue
        if not steps:
            return None
        return max(steps)

    def remove(self, step: int) -> None:
        path = os.path.join(self.directory, f"ckpt_{step}.json")
        if os.path.exists(path):
            os.remove(path)
        self._remove_meta(step)

    def _remove_meta(self, step: int) -> None:
        meta_path = os.path.join(self.directory, f"ckpt_{step}.meta.json")
        if os.path.exists(meta_path):
            os.remove(meta_path)
