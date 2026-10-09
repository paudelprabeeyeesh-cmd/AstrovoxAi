import numpy as np
import os
import json


class CheckpointManager:
    def __init__(self, directory="checkpoints"):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def save(self, step, params, optimizer_state):
        path = os.path.join(self.directory, f"ckpt_{step}.npz")
        np.savez(path, params=np.array(params, dtype=object), step=step)
        meta = {"step": step, "optimizer": str(optimizer_state)}
        with open(os.path.join(self.directory, f"ckpt_{step}.json"), "w") as f:
            json.dump(meta, f)

    def load(self, step):
        path = os.path.join(self.directory, f"ckpt_{step}.npz")
        data = np.load(path, allow_pickle=True)
        return int(data["step"]), list(data["params"])

    def latest(self):
        files = [f for f in os.listdir(self.directory) if f.endswith(".npz")]
        if not files:
            return None
        steps = sorted([int(f.replace("ckpt_", "").replace(".npz", "")) for f in files])
        return steps[-1]


class FaultTolerantTrainer:
    def __init__(self, params, checkpoint_dir="checkpoints"):
        self.params = [np.copy(p) for p in params]
        self.manager = CheckpointManager(checkpoint_dir)
        self.node_healthy = True

    def checkpoint(self, step, optimizer_state):
        self.manager.save(step, self.params, optimizer_state)

    def restart(self):
        step = self.manager.latest()
        if step is None:
            return 0, self.params
        loaded_step, loaded_params = self.manager.load(step)
        self.params = loaded_params
        return loaded_step, self.params

    def heartbeat(self):
        return self.node_healthy
