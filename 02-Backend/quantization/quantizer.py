from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class QuantizationParams:
    scale: float
    zero_point: int
    n_bits: int
    symmetric: bool
    qmin: int
    qmax: int


def compute_quantization_params(
    min_val: float,
    max_val: float,
    n_bits: int,
    symmetric: bool = True,
) -> QuantizationParams:
    if n_bits <= 0:
        raise ValueError("n_bits must be positive")
    qmin = 0
    qmax = (1 << n_bits) - 1
    if symmetric:
        max_abs = max(abs(min_val), abs(max_val))
        scale = (2 * max_abs) / (qmax - qmin) if max_abs > 0 else 1.0
        zero_point = 0
    else:
        scale = (max_val - min_val) / (qmax - qmin) if max_val > min_val else 1.0
        zero_point = int(round(-min_val / scale))
        zero_point = max(qmin, min(qmax, zero_point))
    return QuantizationParams(
        scale=scale,
        zero_point=zero_point,
        n_bits=n_bits,
        symmetric=symmetric,
        qmin=qmin,
        qmax=qmax,
    )


def quantize_uniform(values: List[float], params: QuantizationParams) -> List[int]:
    return [
        max(params.qmin, min(params.qmax, int(round(v / params.scale + params.zero_point))))
        for v in values
    ]


def dequantize_uniform(quantized: List[int], params: QuantizationParams) -> List[float]:
    return [(q - params.zero_point) * params.scale for q in quantized]


def quantize_dequantize_uniform(values: List[float], params: QuantizationParams) -> List[float]:
    return dequantize_uniform(quantize_uniform(values, params), params)
