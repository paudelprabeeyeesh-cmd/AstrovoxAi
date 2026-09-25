"""Edge AI with federated learning and differential privacy."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class EdgeAIFederatedLearning:
    def __init__(self, model: nn.Module, num_clients: int, client_ids: List[str]):
        self.model = model
        self.num_clients = num_clients
        self.client_ids = client_ids
        self.global_weights = {k: v.clone() for k, v in model.state_dict().items()}
        self.round_metrics: List[Dict[str, Any]] = []
        self.cur_round: int = 0

    def local_train_step(self, client_id: str, data: Dict[str, torch.Tensor], lr: float = 1e-4) -> Dict[str, torch.Tensor]:
        model_copy = type(self.model)()
        model_copy.load_state_dict(self.global_weights)
        optimizer = torch.optim.SGD(model_copy.parameters(), lr=lr)
        input_ids = data.get("input_ids")
        labels = data.get("labels", input_ids)
        logits = model_copy(input_ids)
        loss = torch.nn.functional.cross_entropy(logits.view(-1, logits.size(-1)), labels.view(-1))
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model_copy.parameters(), 1.0)
        optimizer.step()
        return model_copy.state_dict()

    def add_differential_privacy_noise(self, weights: Dict[str, torch.Tensor], noise_multiplier: float = 1.0) -> Dict[str, torch.Tensor]:
        noised = {}
        for name, param in weights.items():
            noise = torch.randn_like(param) * noise_multiplier
            noised[name] = param + noise
        return noised

    def secure_aggregate(self, client_weights: List[Dict[str, torch.Tensor]], sample_weights: Optional[List[float]] = None) -> Dict[str, torch.Tensor]:
        if sample_weights is None:
            sample_weights = [1.0 / len(client_weights)] * len(client_weights)
        aggregated = {}
        for key in self.global_weights:
            aggregated[key] = torch.zeros_like(self.global_weights[key])
            for cw, sw in zip(client_weights, sample_weights):
                aggregated[key] += sw * cw[key]
        self.global_weights = aggregated
        return aggregated

    def run_federated_round(self, client_datasets: Dict[str, Dict[str, torch.Tensor]], num_epochs: int = 1) -> Dict[str, Any]:
        client_weights = []
        for cid in self.client_ids:
            if cid not in client_datasets:
                continue
            for _ in range(num_epochs):
                w = self.local_train_step(cid, client_datasets[cid])
            w = self.add_differential_privacy_noise(w)
            client_weights.append(w)
        aggregated = self.secure_aggregate(client_weights)
        self.model.load_state_dict(aggregated, strict=False)
        self.cur_round += 1
        return {"round": self.cur_round, "round_metrics": self.round_metrics, "num_participants": len(client_weights)}
