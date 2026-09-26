from typing import Dict, List, Optional, Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class MixedPrecisionConfig:
    def __init__(self, fp32_layers: Optional[List[str]] = None, fp16_layers: Optional[List[str]] = None, bf16_layers: Optional[List[str]] = None):
        self.fp32_layers = fp32_layers or []
        self.fp16_layers = fp16_layers or []
        self.bf16_layers = bf16_layers or []

    def get_precision(self, layer_name: str) -> torch.dtype:
        for name in self.fp32_layers:
            if name in layer_name:
                return torch.float32
        for name in self.bf16_layers:
            if name in layer_name:
                return torch.bfloat16
        return torch.float16


class MixedPrecisionManager:
    def __init__(self, config: MixedPrecisionConfig):
        self.config = config

    def apply(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            precision = self.config.get_precision(name)
            if precision == torch.float16:
                module.half()
            elif precision == torch.bfloat16:
                module.to(torch.bfloat16)
            else:
                module.float()
        return model

    def get_layer_precision(self, layer_name: str) -> str:
        precision = self.config.get_precision(layer_name)
        if precision == torch.float16:
            return "fp16"
        elif precision == torch.bfloat16:
            return "bf16"
        return "fp32"


class AutoMixedPrecision:
    def __init__(self, model: nn.Module, threshold: float = 1e-4):
        self.model = model
        self.threshold = threshold
        self.sensitive_layers: List[str] = []

    def detect_sensitive_layers(self, sample_input: torch.Tensor) -> List[str]:
        self.model.eval()
        with torch.no_grad():
            baseline = self.model(sample_input)
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear):
                original_params = module.weight.data.clone()
                module.half()
                with torch.no_grad():
                    fp16_out = self.model(sample_input)
                module.weight.data = original_params
                relative_error = (baseline - fp16_out).norm() / baseline.norm()
                if relative_error > self.threshold:
                    self.sensitive_layers.append(name)
        return self.sensitive_layers

    def apply(self, sample_input: torch.Tensor) -> nn.Module:
        sensitive = self.detect_sensitive_layers(sample_input)
        config = MixedPrecisionConfig(fp32_layers=sensitive)
        return MixedPrecisionManager(config).apply(self.model)
