from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.quantization.int8_quantization import INT8Quantizer
from ASTROVOX_AI.ai_core.quantization.gptq import GPTQQuantizer
from ASTROVOX_AI.ai_core.cuda.cuda_mixed_precision import CUDAMixedPrecision


class EdgeAIDeployment:
    def __init__(self, model: nn.Module, target_device: str = 'cpu', optimize: bool = True):
        self.model = model
        self.target_device = target_device
        self.optimize = optimize
        self.optimized_model = model

    def optimize_for_edge(self) -> nn.Module:
        if self.target_device == 'cpu':
            self.optimized_model = torch.quantization.quantize_dynamic(self.model, {nn.Linear}, dtype=torch.qint8)
        elif self.target_device == 'mobile':
            self.optimized_model = torch.jit.script(self.model)
            self.optimized_model = torch.jit.optimize_for_inference(self.optimized_model)
        elif self.target_device == 'tpu':
            self._optimize_for_tpu()
        return self.optimized_model

    def _optimize_for_tpu(self) -> None:
        try:
            import torch_xla
            import torch_xla.core.xla_model as xm
            self.optimized_model = self.optimized_model.to(xm.xla_device())
        except ImportError:
            pass

    def quantize_aware_training(self) -> nn.Module:
        self.model.qconfig = torch.quantization.get_default_qat_qconfig('fbgemm')
        torch.quantization.prepare_qat(self.model, inplace=True)
        return self.model

    def prune_model(self, amount: float = 0.3) -> nn.Module:
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear):
                torch.nn.utils.prune.l1_unstructured(module, name='weight', amount=amount)
        return self.model
