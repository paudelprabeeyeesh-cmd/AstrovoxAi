import torch
import torch.nn as nn
import logging

logger = logging.getLogger(__name__)


class FP16Quantizer:
    def __init__(self, loss_scale: float = 65536.0):
        self.loss_scale = loss_scale

    def quantize(self, model: nn.Module) -> nn.Module:
        return model.half()

    def quantize_activation(self, x: torch.Tensor) -> torch.Tensor:
        return x.half()

    def scale_loss(self, loss: torch.Tensor) -> torch.Tensor:
        return loss * self.loss_scale

    def unscale_loss(self, loss: torch.Tensor) -> torch.Tensor:
        return loss / self.loss_scale


class BF16Quantizer:
    def __init__(self):
        pass

    def quantize(self, model: nn.Module) -> nn.Module:
        return model.to(torch.bfloat16)

    def quantize_activation(self, x: torch.Tensor) -> torch.Tensor:
        return x.to(torch.bfloat16)

    def is_available(self) -> bool:
        return torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8
