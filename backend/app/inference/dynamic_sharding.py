"""Dynamic request sharding across inference nodes."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ShardConfig:
    shard_id: int
    nodes: List[str]
    key_range: Tuple[str, str] = ("", "")
    capacity: int = 100
    current_load: int = 0


class DynamicSharding:
    def __init__(self, num_shards: int = 4, reshard_callback: Optional[Callable] = None):
        self.num_shards = num_shards
        self.shards: List[ShardConfig] = [
            ShardConfig(shard_id=i, nodes=[], key_range=("", ""))
            for i in range(num_shards)
        ]
        self._key_to_shard: Dict[str, int] = {}
        self._reshard_callback = reshard_callback
        self._load_threshold = 0.8

    def get_shard_for_key(self, key: str) -> int:
        if key in self._key_to_shard:
            return self._key_to_shard[key]
        shard_id = int(hashlib.md5(key.encode()).hexdigest(), 16) % self.num_shards
        self._key_to_shard[key] = shard_id
        return shard_id

    def get_shard_by_session(self, session_id: str) -> int:
        return self.get_shard_for_key(f"session:{session_id}")

    def assign_node(self, shard_id: int, node_id: str) -> None:
        shard = self.shards[shard_id]
        if node_id not in shard.nodes:
            shard.nodes.append(node_id)

    def remove_node(self, shard_id: int, node_id: str) -> None:
        shard = self.shards[shard_id]
        shard.nodes = [n for n in shard.nodes if n != node_id]

    def update_shard_load(self, shard_id: int, load: int) -> None:
        shard = self.shards[shard_id]
        shard.current_load = load
        if load > shard.capacity * self._load_threshold and self._reshard_callback:
            self._reshard_callback(shard_id)

    def rebalance(self) -> Dict[int, List[str]]:
        assignments: Dict[int, List[str]] = {}
        all_nodes = [n for shard in self.shards for n in shard.nodes]
        if not all_nodes:
            return assignments
        avg_load = sum(s.current_load for s in self.shards) / max(len(self.shards), 1)
        for shard in self.shards:
            if shard.current_load > avg_load * 1.5:
                overflow = shard.current_load - avg_load
                target_shards = sorted(range(self.num_shards), key=lambda i: self.shards[i].current_load)[:2]
                for target_id in target_shards:
                    if shard.nodes and self.shards[target_id].nodes:
                        node = shard.nodes[0]
                        shard.nodes = shard.nodes[1:]
                        self.shards[target_id].nodes.append(node)
            assignments[shard.shard_id] = shard.nodes.copy()
        return assignments

    def get_shard_status(self) -> Dict[str, Any]:
        return {
            "num_shards": self.num_shards,
            "shards": [
                {
                    "shard_id": s.shard_id,
                    "nodes": s.nodes,
                    "load": s.current_load,
                    "capacity": s.capacity,
                    "utilization": s.current_load / max(s.capacity, 1),
                }
                for s in self.shards
            ],
        }

    def route_request(self, key: str, request: Any) -> Tuple[int, Any]:
        shard_id = self.get_shard_for_key(key)
        shard = self.shards[shard_id]
        if not shard.nodes:
            raise RuntimeError(f"No nodes available for shard {shard_id}")
        self.update_shard_load(shard_id, shard.current_load + 1)
        return shard_id, request
