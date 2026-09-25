from typing import Optional, Dict, Any
import torch
import torch.nn as nn


class INT8Quantizer:
    def __init__(self, calibration_loader=None, num_calibration_batches: int = 100):
        self.calibration_loader = calibration_loader
        self.num_calibration_batches = num_calibration_batches
        self.scales: Dict[str, float] = {}
        self.zero_points: Dict[str, int] = {}

    def calibrate(self, model: nn.Module) -> None:
        model.eval()
        with torch.no_grad():
            for i, batch in enumerate(self.calibration_loader):
                if i >= self.num_calibration_batches:
                    break
                model(batch)

    def quantize(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data
                scale = weight.abs().max() / 127.0
                self.scales[name + '.weight'] = scale.item()
                module.weight.data = (weight / scale).round().clamp(-128, 127).to(torch.int8)
                module.weight.data = module.weight.data.float() * scale
        return model

    def quantize_activation(self, x: torch.Tensor, key: str) -> torch.Tensor:
        scale = self.scales.get(key, x.abs().max() / 127.0)
        return (x / scale).round().clamp(-128, 127).to(torch.int8).float() * scale
