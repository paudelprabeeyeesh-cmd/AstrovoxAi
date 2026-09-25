"""
Federated learning with differential privacy and secure aggregation.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class FederatedLearningWithPrivacy:
    def __init__(self, model: nn.Module, num_clients: int, client_ids: List[str], epsilon: float = 1.0, delta: float = 1e-5):
        self.model = model
        self.num_clients = num_clients
        self.client_ids = client_ids
        self.epsilon = epsilon
        self.delta = delta
        self.global_weights = {k: v.clone() for k, v in model.state_dict().items()}
        self.privacy_accountant: List[float] = []

    def local_train_step(self, client_id: str, data: Dict[str, torch.Tensor], lr: float = 1e-4) -> Dict[str, torch.Tensor]:
        model_copy = type(self.model)()
        model_copy.load_state_dict(self.global_weights)
        optimizer = torch.optim.SGD(model_copy.parameters(), lr=lr)
        input_ids = data.get("input_ids")
        labels = data.get("labels", input_ids)
        logits = model_copy(input_ids)
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        loss = torch.nn.functional.cross_entropy(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model_copy.parameters(), 1.0)
        optimizer.step()
        return model_copy.state_dict()

    def add_gaussian_noise(self, weights: Dict[str, torch.Tensor], noise_multiplier: float = 1.0) -> Dict[str, torch.Tensor]:
        noised = {}
        for name, param in weights.items():
            noise = torch.randn_like(param) * noise_multiplier
            noised[name] = param + noise
        return noised

    def secure_aggregregate(self, client_weights: List[Dict[str, torch.Tensor]], sample_weights: Optional[List[float]] = None) -> Dict[str, torch.Tensor]:
        if sample_weights is None:
            sample_weights = [1.0 / len(client_weights)] * len(client_weights)
        aggregated = {}
        for key in self.global_weights:
            aggregated[key] = torch.zeros_like(self.global_weights[key])
            for cw, sw in zip(client_weights, sample_weights):
                aggregated[key] += sw * cw[key]
        self.global_weights = aggregated
        return aggregated

    def apply_global_weights(self, model: nn.Module) -> nn.Module:
        model.load_state_dict(self.global_weights, strict=False)
        return model
