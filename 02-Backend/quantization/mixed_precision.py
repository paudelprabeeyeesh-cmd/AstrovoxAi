from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from quantization.quantizer import QuantizationParams


@dataclass
class LayerPrecisionConfig:
    layer_name: str
    n_bits: int
    weight_sensitivity: float = 1.0
    activation_sensitivity: float = 1.0


@dataclass
class MixedPrecisionConfig:
    layers: List[LayerPrecisionConfig]
    default_n_bits: int = 8


def assign_precision_by_sensitivity(
    layer_sensitivities: Dict[str, float],
    available_bits: List[int],
    default_n_bits: int = 8,
) -> List[LayerPrecisionConfig]:
    if not available_bits:
        raise ValueError("available_bits must not be empty")
    if not layer_sensitivities:
        return []
    max_bits = max(available_bits)
    min_bits = min(available_bits)
    mid_bits = available_bits[len(available_bits) // 2]
    configs = []
    for name, sensitivity in layer_sensitivities.items():
        if sensitivity >= 0.8:
            bits = max_bits
        elif sensitivity >= 0.5:
            bits = mid_bits
        else:
            bits = min_bits
        configs.append(
            LayerPrecisionConfig(
                layer_name=name,
                n_bits=bits,
                weight_sensitivity=sensitivity,
            )
        )
    return configs


def estimate_mixed_precision_cost(
    configs: List[LayerPrecisionConfig],
    total_params: int,
) -> float:
    if not configs:
        return 0.0
    avg_bits = sum(c.n_bits for c in configs) / len(configs)
    return total_params * avg_bits / 8.0
