import numpy as np
from typing import Dict, List, Optional, Any
from .snapshot_versioning import SnapshotVersioning


class AliasManagement:
    def __init__(self, snapshot_store: SnapshotVersioning):
        self.snapshot_store = snapshot_store
        self.aliases: Dict[str, str] = {}
        self.alias_history: Dict[str, List[Dict[str, Any]]] = {}

    def create_alias(self, alias_name: str, snapshot_id: str) -> None:
        if alias_name in self.aliases:
            raise ValueError(f"Alias {alias_name} already exists")

        self.snapshot_store.get_snapshot(snapshot_id)
        self.aliases[alias_name] = snapshot_id
        self.alias_history[alias_name] = [{
            "snapshot_id": snapshot_id,
            "timestamp": np.datetime64('now').astype(str)
        }]

    def resolve_alias(self, alias_name: str) -> str:
        if alias_name not in self.aliases:
            raise KeyError(f"Alias {alias_name} not found")
        return self.aliases[alias_name]

    def update_alias(self, alias_name: str, new_snapshot_id: str) -> None:
        if alias_name not in self.aliases:
            raise KeyError(f"Alias {alias_name} not found")

        self.snapshot_store.get_snapshot(new_snapshot_id)

        old_snapshot_id = self.aliases[alias_name]
        self.aliases[alias_name] = new_snapshot_id
        self.alias_history[alias_name].append({
            "snapshot_id": new_snapshot_id,
            "timestamp": np.datetime64('now').astype(str),
            "previous_snapshot_id": old_snapshot_id
        })

    def get_alias_history(self, alias_name: str) -> List[Dict[str, Any]]:
        if alias_name not in self.alias_history:
            raise KeyError(f"Alias {alias_name} not found")
        return self.alias_history[alias_name]

    def list_aliases(self) -> Dict[str, str]:
        return dict(self.aliases)

    def get_backward_compatible_snapshot(
        self,
        alias_name: str,
        compatibility_matrix: Optional[Dict[str, List[str]]] = None
    ) -> Optional[str]:
        current_snapshot = self.resolve_alias(alias_name)

        if compatibility_matrix is None:
            return current_snapshot

        compatible_versions = compatibility_matrix.get(current_snapshot, [])
        for snapshot_id in self.snapshot_store.version_history:
            if snapshot_id in compatible_versions:
                return snapshot_id

        return current_snapshot

    def rollback_alias(self, alias_name: str, steps: int = 1) -> str:
        history = self.get_alias_history(alias_name)

        if len(history) <= steps:
            raise ValueError(f"Cannot rollback {steps} steps for alias {alias_name}")

        target_snapshot = history[-(steps + 1)]["snapshot_id"]
        self.aliases[alias_name] = target_snapshot
        return target_snapshot
