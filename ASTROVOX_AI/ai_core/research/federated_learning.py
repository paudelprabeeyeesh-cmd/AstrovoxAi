from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.distributed.nccl import NCCLBackend
from ASTROVOX_AI.ai_core.distributed.parameter_server import ParameterServer


class FederatedLearning:
    def __init__(self, model: nn.Module, num_clients: int, client_ids: List[str], backend: str = 'nccl'):
        self.model = model
        self.num_clients = num_clients
        self.client_ids = client_ids
        self.backend = NCCLBackend(num_clients, list(range(num_clients)))
        self.global_weights = {k: v.clone() for k, v in model.state_dict().items()}

    def aggregate(self, client_weights: List[Dict[str, torch.Tensor]], weights: Optional[List[float]] = None) -> Dict[str, torch.Tensor]:
        if weights is None:
            weights = [1.0 / len(client_weights)] * len(client_weights)
        aggregated = {}
        for key in self.global_weights:
            aggregated[key] = torch.zeros_like(self.global_weights[key])
            for client_weight, weight in zip(client_weights, weights):
                aggregated[key] += weight * client_weight[key]
        self.global_weights = aggregated
        return aggregated

    def federated_average(self, client_weights: List[Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
        return self.aggregate(client_weights)

    def apply_global_weights(self, model: nn.Module) -> nn.Module:
        model.load_state_dict(self.global_weights, strict=False)
        return model

    def differential_privacy_step(self, client_weights: Dict[str, torch.Tensor], noise_scale: float = 0.01) -> Dict[str, torch.Tensor]:
        noisy_weights = {}
        for key, weight in client_weights.items():
            noise = torch.randn_like(weight) * noise_scale
            noisy_weights[key] = weight + noise
        return noisy_weights
