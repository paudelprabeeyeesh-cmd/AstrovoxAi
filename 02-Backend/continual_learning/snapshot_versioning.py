import numpy as np
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class ModelSnapshot:
    snapshot_id: str
    model_state: Dict[str, np.ndarray]
    metadata: Dict[str, Any]
    created_at: str
    parent_snapshot_id: Optional[str] = None

    def compute_hash(self) -> str:
        state_str = json.dumps({
            k: v.tolist() for k, v in self.model_state.items()
        }, sort_keys=True)
        return hashlib.sha256(state_str.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "model_state": {k: v.tolist() for k, v in self.model_state.items()},
            "metadata": self.metadata,
            "created_at": self.created_at,
            "parent_snapshot_id": self.parent_snapshot_id,
            "hash": self.compute_hash()
        }


class SnapshotVersioning:
    def __init__(self):
        self.snapshots: Dict[str, ModelSnapshot] = {}
        self.version_history: List[str] = []

    def create_snapshot(
        self,
        snapshot_id: str,
        model_state: Dict[str, np.ndarray],
        metadata: Optional[Dict[str, Any]] = None,
        parent_snapshot_id: Optional[str] = None
    ) -> ModelSnapshot:
        if snapshot_id in self.snapshots:
            raise ValueError(f"Snapshot {snapshot_id} already exists")

        snapshot = ModelSnapshot(
            snapshot_id=snapshot_id,
            model_state=model_state,
            metadata=metadata or {},
            created_at=datetime.utcnow().isoformat(),
            parent_snapshot_id=parent_snapshot_id
        )

        self.snapshots[snapshot_id] = snapshot
        self.version_history.append(snapshot_id)
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> ModelSnapshot:
        if snapshot_id not in self.snapshots:
            raise KeyError(f"Snapshot {snapshot_id} not found")
        return self.snapshots[snapshot_id]

    def verify_snapshot(self, snapshot_id: str) -> bool:
        snapshot = self.get_snapshot(snapshot_id)
        stored_hash = snapshot.to_dict().get("hash")
        computed_hash = snapshot.compute_hash()
        return stored_hash == computed_hash

    def get_ancestry(self, snapshot_id: str) -> List[str]:
        ancestry = []
        current = snapshot_id
        visited = set()

        while current and current not in visited:
            if current not in self.snapshots:
                break
            ancestry.append(current)
            visited.add(current)
            current = self.snapshots[current].parent_snapshot_id

        return ancestry

    def compare_snapshots(self, snapshot_id_a: str, snapshot_id_b: str) -> Dict[str, Any]:
        snap_a = self.get_snapshot(snapshot_id_a)
        snap_b = self.get_snapshot(snapshot_id_b)

        comparison = {
            "snapshot_a": snapshot_id_a,
            "snapshot_b": snapshot_id_b,
            "layer_diffs": {}
        }

        all_layers = set(snap_a.model_state.keys()) | set(snap_b.model_state.keys())

        for layer in all_layers:
            if layer in snap_a.model_state and layer in snap_b.model_state:
                diff = np.abs(snap_a.model_state[layer] - snap_b.model_state[layer])
                comparison["layer_diffs"][layer] = {
                    "max_diff": float(np.max(diff)),
                    "mean_diff": float(np.mean(diff)),
                    "l2_norm": float(np.linalg.norm(diff))
                }
            elif layer in snap_a.model_state:
                comparison["layer_diffs"][layer] = {"status": "only_in_a"}
            else:
                comparison["layer_diffs"][layer] = {"status": "only_in_b"}

        return comparison
