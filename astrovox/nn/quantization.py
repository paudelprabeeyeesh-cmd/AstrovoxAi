"""Quantization utilities for INT8/INT4 inference and training.

Provides symmetric and asymmetric quantization along with calibration
helpers. Quantized weights are stored as int8 or int4 tensors and require
a scale factor to reconstruct approximate float values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from astrovox.tensor.tensor import Tensor


@dataclass(frozen=True)
class QuantizationParams:
    scale: float
    zero_point: float = 0.0
    quant_type: str = "int8"


def quantize_tensor(tensor: Tensor, dtype: str = "int8") -> tuple[np.ndarray, QuantizationParams]:
    array = tensor.numpy()
    if dtype == "int4":
        levels = 16
        target = np.int8
    else:
        levels = 256
        target = np.int8
    q_min = 0 if dtype == "uint8" else -levels // 2
    q_max = levels - 1 if dtype == "uint8" else levels // 2 - 1
    scale = (np.max(array) - np.min(array)) / (q_max - q_min)
    if scale == 0:
        scale = 1.0
    zero_point = q_min - np.min(array) / scale
    quantized = np.clip(np.round(array / scale + zero_point), q_min, q_max).astype(target)
    return quantized, QuantizationParams(scale=float(scale), zero_point=float(zero_point), quant_type=dtype)


def dequantize_tensor(quantized: np.ndarray, params: QuantizationParams) -> np.ndarray:
    return (quantized.astype(np.float32) - params.zero_point) * params.scale


class QuantizedLinear:
    """Linear layer using quantized weights."""

    def __init__(self, weight: Tensor, bias: Optional[Tensor] = None, dtype: str = "int8") -> None:
        self.quantized_weight, self.q_params = quantize_tensor(weight, dtype=dtype)
        self.bias = bias.numpy() if bias is not None else None
        self.in_features = weight.shape.dims[-1]
        self.out_features = weight.shape.dims[0]

    def forward(self, x: np.ndarray) -> np.ndarray:
        weight = dequantize_tensor(self.quantized_weight, self.q_params)
        out = np.matmul(x, weight.T)
        if self.bias is not None:
            out = out + self.bias
        return out
