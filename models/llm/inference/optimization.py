import os
import logging
from typing import Optional, Dict, Any

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class KVCache:
    def __init__(self):
        self.key_cache: Optional[torch.Tensor] = None
        self.value_cache: Optional[torch.Tensor] = None
        self.cache_len = 0

    def update(self, key: torch.Tensor, value: torch.Tensor):
        if self.key_cache is None:
            self.key_cache = key
            self.value_cache = value
        else:
            self.key_cache = torch.cat([self.key_cache, key], dim=2)
            self.value_cache = torch.cat([self.value_cache, value], dim=2)
        self.cache_len = self.key_cache.size(2)

    def get(self):
        return self.key_cache, self.value_cache

    def clear(self):
        self.key_cache = None
        self.value_cache = None
        self.cache_len = 0


class QuantizedLinear(nn.Module):
    def __init__(self, linear: nn.Linear, dtype: torch.dtype = torch.int8):
        super().__init__()
        self.in_features = linear.in_features
        self.out_features = linear.out_features
        self.weight = nn.Parameter(linear.weight.data.clone())
        self.scale = nn.Parameter(torch.ones(self.out_features, 1))
        self.dtype = dtype

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        w = self.weight * self.scale
        return torch.nn.functional.linear(x, w, None)


def quantize_model(model: nn.Module, dtype: torch.dtype = torch.int8) -> nn.Module:
    for name, module in list(model.named_modules()):
        if isinstance(module, nn.Linear):
            parent_name = name.rsplit(".", 1)[0] if "." in name else ""
            attr_name = name.rsplit(".", 1)[-1] if "." in name else name
            parent = model if parent_name == "" else getattr(model, parent_name)
            quantized = QuantizedLinear(module, dtype=dtype)
            setattr(parent, attr_name, quantized)
    return model


class InferenceOptimizer:
    def __init__(self, model: nn.Module, tokenizer, device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.kv_cache = KVCache()

    def enable_kv_cache(self):
        for name, module in self.model.named_modules():
            if hasattr(module, "use_kv_cache"):
                module.use_kv_cache = True

    def generate(self, prompt: str, max_new_tokens: int = 100, temperature: float = 1.0, top_k: Optional[int] = None) -> str:
        from ..inference.generate import generate
        return generate(self.model, self.tokenizer, prompt, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, device=self.device)
