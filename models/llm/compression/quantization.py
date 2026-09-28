from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

from models.llm.quantization import (
    QuantizationConfig,
    QuantizationFormat,
    QuantizedLinear,
    _dequantize_per_tensor,
    _quantize_per_tensor_int8,
    calibrate_model,
)

logger = logging.getLogger(__name__)


@dataclass
class INT4QuantizationConfig:
    group_size: int = 32
    symmetric: bool = True
    clip_ratio: float = 1.0


def quantize_int4_groupwise(
    weight: torch.Tensor,
    config: INT4QuantizationConfig,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
    if weight.dim() != 2:
        raise ValueError(f"INT4 quantization requires 2D tensor, got {weight.dim()}D")

    out_features, in_features = weight.shape
    group_size = config.group_size

    if in_features % group_size != 0:
        padded_features = ((in_features + group_size - 1) // group_size) * group_size
        padding = padded_features - in_features
        weight = F.pad(weight, (0, padding))
        in_features = padded_features

    num_groups = in_features // group_size
    weight_groups = weight.reshape(out_features, num_groups, group_size)

    if config.symmetric:
        abs_max = weight_groups.abs().amax(dim=-1, keepdim=True)
        scale = abs_max / 7.0
        scale = torch.where(abs_max == 0, torch.ones_like(scale), scale)
        q = torch.clamp(torch.round(weight_groups / scale), -8, 7).to(torch.int8)
        return q.reshape(out_features, in_features), scale.squeeze(-1), None

    min_val = weight_groups.amin(dim=-1, keepdim=True)
    max_val = weight_groups.amax(dim=-1, keepdim=True)
    scale = (max_val - min_val) / 15.0
    scale = torch.where((max_val - min_val) == 0, torch.ones_like(scale), scale)
    zero_point = torch.round(-min_val / scale).clamp(0, 15).to(torch.int32)
    q = torch.clamp(torch.round(weight_groups / scale) + zero_point, 0, 15).to(torch.int8)
    return q.reshape(out_features, in_features), scale.squeeze(-1), zero_point.squeeze(-1)


def dequantize_int4_groupwise(
    q: torch.Tensor,
    scale: torch.Tensor,
    zero_point: torch.Tensor | None,
    original_in_features: int,
    config: INT4QuantizationConfig,
) -> torch.Tensor:
    current_in_features = q.shape[1]

    if config.symmetric:
        scale_expanded = scale.repeat_interleave(current_in_features // scale.shape[1], dim=1)
        return (q.float() * scale_expanded).float()[:, :original_in_features]

    zp_expanded = zero_point.repeat_interleave(current_in_features // zero_point.shape[1], dim=1)
    scale_expanded = scale.repeat_interleave(current_in_features // scale.shape[1], dim=1)
    return ((q.float() - zp_expanded) * scale_expanded).float()[:, :original_in_features]


class INT4QuantizedLinear(nn.Module):
    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        config: QuantizationConfig | None = None,
        int4_config: INT4QuantizationConfig | None = None,
    ) -> None:
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.config = config or QuantizationConfig(weight_bits=4)
        self.int4_config = int4_config or INT4QuantizationConfig()
        self._quantized_weight: torch.Tensor | None = None
        self._scale: torch.Tensor | None = None
        self._zero_point: torch.Tensor | None = None
        self._original_in_features = in_features

        self._weight_float = nn.Parameter(torch.empty(out_features, in_features))
        if bias:
            self.bias = nn.Parameter(torch.zeros(out_features))
        else:
            self.register_parameter("bias", None)
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.kaiming_uniform_(self._weight_float, a=5**0.5)
        if self.bias is not None:
            nn.init.zeros_(self.bias)

    @property
    def weight(self) -> nn.Parameter:
        return self._weight_float

    def quantize(self, weight: torch.Tensor) -> None:
        q, scale, zp = quantize_int4_groupwise(weight, self.int4_config)
        self._quantized_weight = q
        self._scale = scale
        self._zero_point = zp
        self._weight_float.data = dequantize_int4_groupwise(
            q, scale, zp, self._original_in_features, self.int4_config
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weight = self._weight_float
        if weight.dtype != x.dtype:
            x = x.to(weight.dtype)
        return F.linear(x, weight, self.bias)

    def extra_repr(self) -> str:
        return (
            f"in_features={self.in_features}, out_features={self.out_features}, "
            f"weight_bits=4, group_size={self.int4_config.group_size}"
        )


class GPTQStyleQuantizer:
    def __init__(
        self,
        config: QuantizationConfig,
        calibration_loader: Any = None,
    ) -> None:
        self.config = config
        self.calibration_loader = calibration_loader

    def quantize(self, model: nn.Module) -> nn.Module:
        from models.llm.quantization import quantize_model
        return quantize_model(model, self.config, calibration_loader=self.calibration_loader)


class AWQStyleQuantizer:
    def __init__(
        self,
        config: QuantizationConfig,
        calibration_loader: Any = None,
    ) -> None:
        self.config = config
        self.calibration_loader = calibration_loader

    def quantize(self, model: nn.Module) -> nn.Module:
        from models.llm.quantization import quantize_model
        return quantize_model(model, self.config, calibration_loader=self.calibration_loader)


class QATTrainer:
    def __init__(
        self,
        model: nn.Module,
        config: QuantizationConfig,
        optimizer_cls: type[torch.optim.Optimizer] | None = None,
        optimizer_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self.model = model
        self.config = config
        self.optimizer_cls = optimizer_cls or torch.optim.AdamW
        self.optimizer_kwargs = optimizer_kwargs or {"lr": config.learning_rate}

    def prepare_model(self) -> nn.Module:
        from models.llm.quantization import QuantizedModelWrapper
        return QuantizedModelWrapper(self.model, config=self.config)

    def train_step(
        self,
        batch: Any,
        optimizer: torch.optim.Optimizer,
    ) -> torch.Tensor:
        self.model.train()
        optimizer.zero_grad()

        if isinstance(batch, (list, tuple)):
            inputs = batch[0]
            labels = batch[1] if len(batch) > 1 else None
        else:
            inputs = batch
            labels = None

        outputs = self.model(inputs)

        if labels is not None:
            if hasattr(outputs, "logits"):
                loss = F.cross_entropy(outputs.logits, labels)
            else:
                loss = F.mse_loss(outputs, labels)
        else:
            loss = outputs.sum() if isinstance(outputs, torch.Tensor) else outputs.loss

        loss.backward()
        optimizer.step()
        return loss
