import os
import sys

import pytest
import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.quantization import (
    QuantizationConfig,
    QuantizationFormat,
    QuantizationMethod,
    QuantizedLinear,
    QuantizedModelWrapper,
    get_supported_formats,
    get_supported_methods,
)


class TestQuantizationConfig:
    def test_default_config(self):
        cfg = QuantizationConfig()
        assert cfg.format == QuantizationFormat.FP16
        assert cfg.method == QuantizationMethod.WEIGHT_ONLY

    def test_from_dict(self):
        cfg = QuantizationConfig.from_dict({"format": "int8_symmetric", "method": "weight_only"})
        assert cfg.format == QuantizationFormat.INT8_SYMMETRIC

    def test_to_dict_roundtrip(self):
        cfg = QuantizationConfig(format=QuantizationFormat.BF16, method=QuantizationMethod.POST_TRAINING)
        d = cfg.to_dict()
        assert d["format"] == "bf16"
        assert d["method"] == "ptq"

    def test_effective_format_fallback(self):
        cfg = QuantizationConfig(
            format=QuantizationFormat.GPTQ,
            enable_fallback=True,
            fallback_format=QuantizationFormat.INT8_SYMMETRIC,
        )
        assert cfg.effective_format == QuantizationFormat.INT8_SYMMETRIC


class TestQuantizedLinear:
    def test_fp16_passthrough(self):
        cfg = QuantizationConfig(format=QuantizationFormat.FP16)
        layer = QuantizedLinear(16, 32, config=cfg)
        x = torch.randn(2, 16)
        out = layer(x)
        assert out.shape == (2, 32)

    def test_int8_quantize_dequantize(self):
        cfg = QuantizationConfig(format=QuantizationFormat.INT8_SYMMETRIC, per_channel=False)
        layer = QuantizedLinear(16, 32, bias=False, config=cfg)
        weight = torch.randn(32, 16)
        layer.quantize(weight)
        assert layer._quantized_weight is not None
        x = torch.randn(2, 16)
        out = layer(x)
        assert out.shape == (2, 32)

    def test_repr(self):
        cfg = QuantizationConfig(format=QuantizationFormat.INT8_SYMMETRIC)
        layer = QuantizedLinear(8, 8, config=cfg)
        r = layer.extra_repr()
        assert "in_features=8" in r


class TestQuantizedModelWrapper:
    def test_wrap_model(self):
        model = torch.nn.Sequential(torch.nn.Linear(16, 32), torch.nn.ReLU(), torch.nn.Linear(32, 8))
        cfg = QuantizationConfig(format=QuantizationFormat.INT8_SYMMETRIC)
        wrapper = QuantizedModelWrapper(model, config=cfg)
        x = torch.randn(2, 16)
        out = wrapper(x)
        assert out.shape == (2, 8)

    def test_get_quantized_layers(self):
        model = torch.nn.Sequential(torch.nn.Linear(16, 32))
        cfg = QuantizationConfig(format=QuantizationFormat.INT8_SYMMETRIC)
        wrapper = QuantizedModelWrapper(model, config=cfg)
        layers = wrapper.get_quantized_layers()
        assert len(layers) == 1


class TestSupportedFormats:
    def test_get_supported_formats(self):
        formats = get_supported_formats()
        assert "fp16" in formats
        assert "int8_symmetric" in formats

    def test_get_supported_methods(self):
        methods = get_supported_methods()
        assert "weight_only" in methods
        assert "ptq" in methods
