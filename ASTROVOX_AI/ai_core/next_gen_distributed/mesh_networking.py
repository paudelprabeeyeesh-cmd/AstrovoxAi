"""Mesh networking for AI inference routing and model aggregation."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import torch

logger = logging.getLogger(__name__)


@dataclass
class MeshNode:
    node_id: str
    address: str
    capabilities: List[str] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    load: float = 0.0


class MeshNetworkingForAI:
    def __init__(self, local_node_id: str, local_address: str):
        self.local_node_id = local_node_id
        self.local_address = local_address
        self.nodes: Dict[str, MeshNode] = {local_node_id: MeshNode(node_id=local_node_id, address=local_address)}
        self.routing_table: Dict[str, str] = {}
        self.message_queue: deque = deque(maxlen=10000)

    def register_node(self, node_id: str, address: str, capabilities: Optional[List[str]] = None) -> None:
        self.nodes[node_id] = MeshNode(node_id=node_id, address=address, capabilities=capabilities or [])
        self._update_routing()

    def _update_routing(self) -> None:
        for node_id in self.nodes:
            if node_id != self.local_node_id:
                self.routing_table[node_id] = node_id

    def route_inference_request(self, target_capability: str, payload: Dict[str, Any]) -> Optional[str]:
        candidates = [n.node_id for n in self.nodes.values() if target_capability in n.capabilities and n.node_id != self.local_node_id]
        if not candidates:
            return None
        best = min(candidates, key=lambda nid: self.nodes[nid].latency_ms)
        self.message_queue.append({"to": best, "payload": payload, "ts": time.time()})
        return best

    def broadcast_model_update(self, model_delta: Dict[str, Any]) -> List[str]:
        recipients = [nid for nid in self.nodes if nid != self.local_node_id]
        for nid in recipients:
            self.message_queue.append({"to": nid, "payload": {"type": "model_update", "delta": model_delta}, "ts": time.time()})
        return recipients

    def topology_aware_aggregation(self, model_shards: Dict[str, Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
        aggregated: Dict[str, torch.Tensor] = {}
        count = 0
        for shard in model_shards.values():
            for k, v in shard.items():
                aggregated[k] = aggregated.get(k, torch.zeros_like(v)) + v
            count += 1
        if count:
            for k in aggregated:
                aggregated[k] = aggregated[k] / count
        return aggregated
