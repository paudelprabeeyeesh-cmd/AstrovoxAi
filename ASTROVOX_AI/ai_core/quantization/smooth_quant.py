from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class SmoothQuantizer:
    def __init__(self, calibration_loader=None, num_calibration_batches: int = 100, alpha: float = 0.5):
        self.calibration_loader = calibration_loader
        self.num_calibration_batches = num_calibration_batches
        self.alpha = alpha
        self.scales: Dict[str, torch.Tensor] = {}

    def _compute_scale(self, x: torch.Tensor) -> torch.Tensor:
        return x.abs().pow(self.alpha).max(dim=1, keepdim=True).values.clamp(min=1e-5)

    def calibrate(self, model: nn.Module) -> None:
        model.eval()
        with torch.no_grad():
            for i, batch in enumerate(self.calibration_loader):
                if i >= self.num_calibration_batches:
                    break
                model(batch)

    def smooth(self, model: nn.Module) -> nn.Module:
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data
                scale = self._compute_scale(weight)
                self.scales[name + '.weight'] = scale
                module.weight.data = weight / scale
                if hasattr(module, 'bias') and module.bias is not None:
                    module.bias.data = module.bias.data * scale.squeeze()
        return model

    def quantize(self, model: nn.Module) -> nn.Module:
        smoothed = self.smooth(model)
        for name, module in smoothed.named_modules():
            if isinstance(module, nn.Linear):
                weight = module.weight.data
                scale = weight.abs().max() / 127.0
                module.weight.data = (weight / scale).round().clamp(-128, 127).to(torch.int8).float() * scale
        return smoothed
