"""Peer-to-peer model sharing with DHT-style discovery and merging."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import torch

logger = logging.getLogger(__name__)


class P2PModelSharing:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.local_store: Dict[str, Dict[str, Any]] = {}
        self.remote_index: Dict[str, Dict[str, Any]] = {}
        self.transfer_log: List[Dict[str, Any]] = []

    def advertise_model(self, model_hash: str, model_weights: Dict[str, torch.Tensor], metadata: Dict[str, Any]) -> None:
        self.local_store[model_hash] = {"weights": model_weights, "metadata": metadata, "owner": self.node_id}

    def discover(self, query: str) -> List[str]:
        return [h for h, meta in self.local_store.items() if query.lower() in json.dumps(meta).lower()]

    def request_model(self, model_hash: str, peer_id: str) -> Optional[Dict[str, Any]]:
        model = self.local_store.get(model_hash)
        if model:
            self.transfer_log.append({"model_hash": model_hash, "from": self.node_id, "to": peer_id, "ts": time.time()})
            return model
        remote = self.remote_index.get(model_hash)
        if remote:
            return remote
        return None

    def merge_models(self, base: Dict[str, torch.Tensor], delta: Dict[str, torch.Tensor], alpha: float = 0.5) -> Dict[str, torch.Tensor]:
        merged = {}
        for key in base:
            merged[key] = alpha * base[key] + (1 - alpha) * delta.get(key, torch.zeros_like(base[key]))
        return merged
