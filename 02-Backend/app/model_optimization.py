"""
Quantization utilities and model optimization for deployment.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class QuantizationManager:
    def __init__(self):
        self.quantizers: Dict[str, Any] = {}
        self.quantized_models: Dict[str, nn.Module] = {}

    def register_quantizer(self, name: str, quantizer: Any) -> None:
        self.quantizers[name] = quantizer

    def quantize(self, model_name: str, model: nn.Module, quantizer_name: str) -> Optional[nn.Module]:
        quantizer = self.quantizers.get(quantizer_name)
        if quantizer is None:
            return None
        quantized = quantizer.quantize_model(model)
        self.quantized_models[model_name] = quantized
        return quantized

    def get_quantized_model(self, model_name: str) -> Optional[nn.Module]:
        return self.quantized_models.get(model_name)

    def benchmark_quantized_model(self, model_name: str, input_shape: tuple, num_runs: int = 100) -> Dict[str, Any]:
        model = self.quantized_models.get(model_name)
        if model is None:
            return {}
        device = next(model.parameters()).device
        dummy = torch.randn(*input_shape, device=device)
        model.eval()
        start = time.time()
        with torch.no_grad():
            for _ in range(num_runs):
                _ = model(dummy)
        elapsed = time.time() - start
        return {'avg_latency_ms': elapsed / num_runs * 1000, 'throughput': num_runs / elapsed}
