from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class LoRALayer(nn.Module):
    def __init__(self, in_features: int, out_features: int, rank: int = 8, alpha: float = 16.0, dropout: float = 0.0):
        super().__init__()
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank
        self.lora_A = nn.Parameter(torch.zeros(in_features, rank))
        self.lora_B = nn.Parameter(torch.zeros(rank, out_features))
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        nn.init.zeros_(self.lora_B)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(x @ self.lora_A) @ self.lora_B * self.scaling


class LoRA:
    @staticmethod
    def inject(model: nn.Module, target_modules: List[str] = None, rank: int = 8, alpha: float = 16.0, dropout: float = 0.0) -> nn.Module:
        if target_modules is None:
            target_modules = ['q_proj', 'k_proj', 'v_proj', 'o_proj']
        for name, module in model.named_modules():
            if any(target in name for target in target_modules) and isinstance(module, nn.Linear):
                lora = LoRALayer(module.in_features, module.out_features, rank, alpha, dropout)
                setattr(module, 'lora', lora)
                original_forward = module.forward
                def make_forward(orig, lora_layer):
                    def forward(x):
                        return orig(x) + lora_layer(x)
                    return forward
                module.forward = make_forward(original_forward, lora)
        return model

    @staticmethod
    def merge(model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if hasattr(module, 'lora'):
                lora = module.lora
                module.weight.data += lora.lora_A @ lora.lora_B * lora.scaling
                delattr(module, 'lora')
                module.forward = module._original_forward
        return model
