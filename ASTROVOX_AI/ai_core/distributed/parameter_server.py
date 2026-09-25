from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
import torch.distributed as dist


class ParameterServer:
    def __init__(self, rank: int, world_size: int, backend: str = 'nccl'):
        self.rank = rank
        self.world_size = world_size
        self.backend = backend
        self.parameters: Dict[str, torch.Tensor] = {}
        self.gradients: Dict[str, torch.Tensor] = {}
        self.param_server_rank = 0

    def push_gradients(self, gradients: Dict[str, torch.Tensor]) -> None:
        for name, grad in gradients.items():
            if self.rank == self.param_server_rank:
                if name not in self.gradients:
                    self.gradients[name] = torch.zeros_like(grad)
                self.gradients[name] += grad
        if self.rank != self.param_server_rank:
            for name, grad in gradients.items():
                dist.send(tensor=grad, dst=self.param_server_rank)

    def pull_parameters(self) -> Dict[str, torch.Tensor]:
        if self.rank == self.param_server_rank:
            return self.parameters
        params = {}
        for name, param in self.parameters.items():
            dist.recv(tensor=param, src=self.param_server_rank)
            params[name] = param.clone()
        return params

    def update_parameters(self, learning_rate: float = 0.01) -> None:
        if self.rank == self.param_server_rank:
            for name in self.parameters:
                if name in self.gradients:
                    self.parameters[name] -= learning_rate * self.gradients[name]
                    self.gradients[name].zero_()

    def broadcast_parameters(self, model: nn.Module) -> None:
        for name, param in model.named_parameters():
            dist.broadcast(param.data, src=self.param_server_rank)
            self.parameters[name] = param.data.clone()
