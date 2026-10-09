from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from quantization.quantizer import (
    QuantizationParams,
    compute_quantization_params,
    quantize_dequantize_uniform,
)


@dataclass
class CalibrationConfig:
    n_bits: int = 8
    symmetric: bool = True
    method: str = "minmax"


def calibrate_minmax(
    values: List[float],
    n_bits: int = 8,
    symmetric: bool = True,
) -> QuantizationParams:
    if not values:
        raise ValueError("values must not be empty")
    min_val = min(values)
    max_val = max(values)
    return compute_quantization_params(min_val, max_val, n_bits, symmetric)


def calibrate_histogram(
    values: List[float],
    n_bits: int = 8,
    symmetric: bool = True,
    bins: int = 100,
) -> QuantizationParams:
    if not values:
        raise ValueError("values must not be empty")
    sorted_vals = sorted(values)
    total = len(sorted_vals)
    lo_idx = max(0, int(total * 0.001))
    hi_idx = min(total - 1, int(total * 0.999))
    min_val = sorted_vals[lo_idx]
    max_val = sorted_vals[hi_idx]
    return compute_quantization_params(min_val, max_val, n_bits, symmetric)


def compute_calibration_error(
    original: List[float],
    reconstructed: List[float],
) -> Dict[str, float]:
    if len(original) != len(reconstructed):
        raise ValueError("Lists must have the same length")
    n = len(original)
    if n == 0:
        return {"mse": 0.0, "mae": 0.0, "max_error": 0.0}
    errors = [abs(o - r) for o, r in zip(original, reconstructed)]
    sq_errors = [e * e for e in errors]
    mse = sum(sq_errors) / n
    mae = sum(errors) / n
    max_error = max(errors)
    return {"mse": mse, "mae": mae, "max_error": max_error}
