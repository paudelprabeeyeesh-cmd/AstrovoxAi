from typing import Dict
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class SparsePruner:
    def __init__(self, sparsity: float = 0.5, method: str = "magnitude"):
        self.sparsity = sparsity
        self.method = method
        self.masks: Dict[str, torch.Tensor] = {}

    def _compute_mask(self, weight: torch.Tensor) -> torch.Tensor:
        flat = weight.abs().flatten()
        k = int(flat.numel() * self.sparsity)
        if k == 0:
            return torch.ones_like(weight)
        threshold = torch.kthvalue(flat, k).values
        return (weight.abs() > threshold).float()

    def prune(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                mask = self._compute_mask(module.weight.data)
                self.masks[name + '.weight'] = mask
                module.weight.data *= mask
        return model

    def apply_mask(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                mask = self.masks.get(name + '.weight', torch.ones_like(module.weight.data))
                module.weight.data *= mask
        return model

    def get_sparsity(self, model: nn.Module) -> float:
        total = 0
        zeros = 0
        for module in model.modules():
            if isinstance(module, nn.Linear):
                total += module.weight.numel()
                zeros += (module.weight == 0).sum().item()
        return zeros / max(1, total)

    def remove_mask(self, model: nn.Module) -> nn.Module:
        for module in model.modules():
            if isinstance(module, nn.Linear):
                name = id(module)
                if name in self.masks:
                    module.weight.data += self.masks[name] * 0
        return model


class StructuredSparsePruner:
    def __init__(self, sparsity: float = 0.5):
        self.sparsity = sparsity

    def prune(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                weight_norm = module.weight.data.abs().sum(dim=1)
                num_keep = max(1, int(weight_norm.numel() * (1 - self.sparsity)))
                _, indices = torch.topk(weight_norm, num_keep)
                mask = torch.zeros_like(module.weight.data)
                mask[indices] = 1.0
                module.weight.data *= mask
        return model
