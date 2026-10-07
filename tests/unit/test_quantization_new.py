"""Tests for quantization utilities."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.nn.quantization import QuantizedLinear, quantize_tensor
from astrovox.tensor.tensor import Tensor


def test_quantize_tensor_returns_int8():
    tensor = Tensor.from_numpy(np.array([1.0, -1.0, 0.5], dtype=np.float32))
    quantized, params = quantize_tensor(tensor)
    assert quantized.dtype == np.int8
    assert params.quant_type == "int8"


def test_quantized_linear_forward_shape():
    weight = Tensor.from_numpy(np.ones((8, 4), dtype=np.float32))
    layer = QuantizedLinear(weight)
    x = np.ones((1, 4), dtype=np.float32)
    result = layer.forward(x)
    assert result.shape == (1, 8)


def test_quantized_linear_with_bias():
    weight = Tensor.from_numpy(np.ones((8, 4), dtype=np.float32))
    bias = Tensor.from_numpy(np.ones((8,), dtype=np.float32))
    layer = QuantizedLinear(weight, bias=bias)
    x = np.ones((1, 4), dtype=np.float32)
    result = layer.forward(x)
    assert result.shape == (1, 8)
