from typing import Dict, Optional
import torch
import torch.nn as nn
from safetensors import safe_open
from safetensors.torch import save_file


class SafeTensorLoader:
    def __init__(self, device: str = 'cpu'):
        self.device = device

    def load(self, path: str, tensor_names: Optional[list] = None) -> Dict[str, torch.Tensor]:
        tensors = {}
        with safe_open(path, framework='pt', device=self.device) as f:
            keys = tensor_names or f.keys()
            for key in keys:
                tensors[key] = f.get_tensor(key)
        return tensors

    def load_model(self, model: nn.Module, path: str, strict: bool = True) -> nn.Module:
        tensors = self.load(path)
        model.load_state_dict(tensors, strict=strict)
        return model

    @staticmethod
    def save(model: nn.Module, path: str) -> None:
        state_dict = model.state_dict()
        save_file(state_dict, path)


class SafeTensorSaver:
    @staticmethod
    def save(state_dict: Dict[str, torch.Tensor], path: str) -> None:
        save_file(state_dict, path)
