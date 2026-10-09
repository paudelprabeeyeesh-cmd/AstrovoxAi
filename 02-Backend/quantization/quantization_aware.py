from __future__ import annotations

from typing import List

from quantization.quantizer import (
    QuantizationParams,
    dequantize_uniform,
    quantize_uniform,
)


class FakeQuantize:
    def __init__(self, n_bits: int = 8, symmetric: bool = True):
        self.n_bits = n_bits
        self.symmetric = symmetric
        self.min_val = float("inf")
        self.max_val = float("-inf")
        self.observer_enabled = True

    def update_observer(self, values: List[float]) -> None:
        if not values:
            return
        self.min_val = min(self.min_val, min(values))
        self.max_val = max(self.max_val, max(values))

    def forward(self, values: List[float]) -> List[float]:
        if self.observer_enabled:
            self.update_observer(values)
        min_val = self.min_val if self.min_val != float("inf") else 0.0
        max_val = self.max_val if self.max_val != float("-inf") else 1.0
        qmax = (1 << self.n_bits) - 1
        if max_val > min_val:
            scale = (max_val - min_val) / qmax
            zero_point = 0 if self.symmetric else int(round(-min_val / scale))
        else:
            scale = 1.0
            zero_point = 0
        params = QuantizationParams(
            scale=scale,
            zero_point=zero_point,
            n_bits=self.n_bits,
            symmetric=self.symmetric,
            qmin=0,
            qmax=qmax,
        )
        quantized = quantize_uniform(values, params)
        return dequantize_uniform(quantized, params)

    def disable_observer(self) -> None:
        self.observer_enabled = False

    def enable_observer(self) -> None:
        self.observer_enabled = True


class StraightThroughEstimator:
    def quantize(self, values: List[float], params: QuantizationParams) -> List[int]:
        return quantize_uniform(values, params)

    def dequantize(self, quantized: List[int], params: QuantizationParams) -> List[float]:
        return dequantize_uniform(quantized, params)

    def fake_quantize(self, values: List[float], params: QuantizationParams) -> List[float]:
        return dequantize_uniform(quantize_uniform(values, params), params)


def simulate_qat_step(values: List[float], n_bits: int = 8, symmetric: bool = True) -> List[float]:
    fq = FakeQuantize(n_bits=n_bits, symmetric=symmetric)
    return fq.forward(values)
