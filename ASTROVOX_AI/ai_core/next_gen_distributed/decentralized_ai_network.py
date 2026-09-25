"""Decentralized AI model network with gossip sync and model registry."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class DecentralizedAIModelNetwork:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.peers: List[str] = []
        self.local_model: Optional[nn.Module] = None
        self.model_registry: Dict[str, Dict[str, Any]] = {}
        self.version_vector: Dict[str, int] = {}

    def register_peer(self, peer_id: str) -> None:
        if peer_id not in self.peers:
            self.peers.append(peer_id)

    def publish_model(self, model_weights: Dict[str, torch.Tensor], metadata: Dict[str, Any]) -> str:
        model_hash = hashlib.sha256(json.dumps({k: v.tolist() for k, v in model_weights.items()}).encode()).hexdigest()
        self.model_registry[model_hash] = {"weights": model_weights, "metadata": metadata, "publisher": self.node_id}
        self.version_vector[self.node_id] = self.version_vector.get(self.node_id, 0) + 1
        return model_hash

    def pull_model(self, model_hash: str) -> Optional[Dict[str, Any]]:
        return self.model_registry.get(model_hash)

    def gossip_sync(self, models: List[Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
        if not models:
            return {}
        avg_weights = {}
        for key in models[0]:
            avg_weights[key] = torch.stack([m[key] for m in models]).mean(dim=0)
        return avg_weights

    def reconcile(self, remote_models: Dict[str, Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
        all_weights = list(self.model_registry.values())
        for v in remote_models.values():
            all_weights.append(v)
        if not all_weights:
            return {}
        return self.gossip_sync([m["weights"] for m in all_weights])
