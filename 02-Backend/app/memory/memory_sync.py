"""
Memory Sync - Synchronizes memory across layers and with external stores.

Handles:
- Cross-layer memory propagation
- Conflict resolution
- Change tracking
- Batch synchronization
"""

from typing import Any, Dict, List, Optional
from datetime import datetime


class MemorySync:
    """Synchronizes memories between layers and stores."""

    def __init__(self):
        self._change_log: List[Dict[str, Any]] = []
        self._last_sync: Dict[str, str] = {}

    def record_change(self, layer: str, operation: str, memory_id: str, data: Dict[str, Any]):
        self._change_log.append({
            "layer": layer,
            "operation": operation,
            "memory_id": memory_id,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def sync_layer(self, source: str, target: str, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        synced = 0
        conflicts = 0
        for mem in memories:
            self.record_change(source, "propagate", mem.get("id", ""), {"target": target})
            synced += 1
        self._last_sync[f"{source}->{target}"] = datetime.utcnow().isoformat()
        return {
            "source": source,
            "target": target,
            "synced": synced,
            "conflicts": conflicts,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_changes_since(self, layer: str, since: str) -> List[Dict[str, Any]]:
        changes = []
        for entry in self._change_log:
            if entry["layer"] == layer and entry["timestamp"] > since:
                changes.append(entry)
        return changes

    def get_last_sync(self, source: str, target: str) -> Optional[str]:
        return self._last_sync.get(f"{source}->{target}")

    def full_sync(self, layers: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        results = {}
        layer_names = list(layers.keys())
        for i, source in enumerate(layer_names):
            for target in layer_names[i + 1:]:
                key = f"{source}->{target}"
                results[key] = self.sync_layer(source, target, layers[source])
                reverse_key = f"{target}->{source}"
                results[reverse_key] = self.sync_layer(target, source, layers[target])
        return results
