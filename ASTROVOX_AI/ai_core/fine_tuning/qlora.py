from typing import Optional, List
import torch.nn as nn
from ASTROVOX_AI.ai_core.quantization.int8_quantization import INT8Quantizer
from ASTROVOX_AI.ai_core.fine_tuning.lora import LoRA


class QLoRA:
    def __init__(self, bits: int = 4, group_size: int = 128, lora_rank: int = 8, lora_alpha: float = 16.0):
        self.bits = bits
        self.group_size = group_size
        self.lora_rank = lora_rank
        self.lora_alpha = lora_alpha
        self.quantizer = INT8Quantizer()

    def prepare(self, model: nn.Module, target_modules: Optional[List[str]] = None) -> nn.Module:
        model = self.quantizer.quantize(model)
        model = LoRA.inject(model, target_modules, rank=self.lora_rank, alpha=self.lora_alpha)
        for name, param in model.named_parameters():
            if 'lora' in name:
                param.requires_grad = True
            else:
                param.requires_grad = False
        return model
