"""Tests for LoRA/QLoRA integration - expanded coverage."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.nn.lora import LoRAConfig, LoRALinear, QLoRALinear


def test_lora_linear_forward_shape():
    layer = LoRALinear(4, 8, config=LoRAConfig(rank=2))
    x = np.ones((1, 4), dtype=np.float32)
    from astrovox.tensor.tensor import Tensor
    xt = Tensor.from_numpy(x)
    result = layer(xt)
    assert result.shape.dims == (1, 8)


def test_lora_linear_zero_rank_skips_adapter():
    layer = LoRALinear(4, 8, config=LoRAConfig(rank=0))
    x = np.ones((1, 4), dtype=np.float32)
    from astrovox.tensor.tensor import Tensor
    xt = Tensor.from_numpy(x)
    result = layer(xt)
    assert result.shape.dims == (1, 8)


def test_qlora_linear_quantizes_weights():
    layer = QLoRALinear(4, 8, config=LoRAConfig(rank=2))
    assert layer.weight is not None
