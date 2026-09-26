from typing import Dict
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class PTQQuantizer:
    def __init__(self, calibration_loader=None, num_calibration_batches: int = 100, bits: int = 8):
        self.calibration_loader = calibration_loader
        self.num_calibration_batches = num_calibration_batches
        self.bits = bits
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
        qmin = -(2 ** (self.bits - 1))
        qmax = 2 ** (self.bits - 1) - 1
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data
                scale = weight.abs().max() / ((qmax - qmin) / 2)
                zero_point = 0
                self.scales[name + '.weight'] = scale.item()
                self.zero_points[name + '.weight'] = zero_point
                module.weight.data = ((weight / scale).round().clamp(qmin, qmax).to(torch.int32).float() - zero_point) * scale
        return model

    def quantize_activation(self, x: torch.Tensor, key: str) -> torch.Tensor:
        scale = self.scales.get(key, x.abs().max() / 127.0)
        zero_point = self.zero_points.get(key, 0)
        return ((x / scale).round().clamp(-128, 127).to(torch.int32).float() - zero_point) * scale
