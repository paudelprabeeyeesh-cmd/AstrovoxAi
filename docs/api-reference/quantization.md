# Quantization API Reference

## `models.llm.quantization.QuantizationConfig`

Configuration dataclass for quantization.

```python
QuantizationConfig(
    format: QuantizationFormat = QuantizationFormat.FP16,
    method: QuantizationMethod = QuantizationMethod.WEIGHT_ONLY,
    weight_bits: int = 8,
    activation_bits: int = 8,
    symmetric: bool = True,
    per_channel: bool = True,
    group_size: int = 128,
    calibration_samples: int = 128,
    learning_rate: float = 1e-5,
    enable_fallback: bool = True,
    fallback_format: QuantizationFormat = QuantizationFormat.INT8_SYMMETRIC,
    device: Optional[torch.device] = None,
)
```

## Quantization Formats

| Format | Description |
|--------|-------------|
| `fp16` | 16-bit floating point |
| `bf16` | Brain floating point |
| `int8_symmetric` | 8-bit symmetric integer |
| `int8_asymmetric` | 8-bit asymmetric integer |
| `gptq` | GPTQ (requires `gptqmodel`) |
| `awq` | AWQ (requires `autoawq`) |
| `gguf` | GGUF (requires `gguf`) |
| `exl2` | EXL2 (requires `exllamav2`) |

## Methods

| Method | Description |
|--------|-------------|
| `weight_only` | Quantize weights only |
| `activation` | Quantize activations |
| `mixed_precision` | Mixed precision quantization |
| `qat` | Quantization-aware training |
| `ptq` | Post-training quantization |

## High-level API

#### `quantize_model(model, config=None, layers_to_quantize=None, calibration_loader=None) -> nn.Module`

Quantize a model with automatic fallback.

#### `get_supported_formats() -> List[str]`

Return formats available in the current environment.

#### `get_supported_methods() -> List[str]`

Return methods available in the current environment.

## Classes

### `QuantizedLinear`

Linear layer with quantized weights. Supports FP16/BF16 passthrough, INT8 symmetric/asymmetric, GPTQ/AWQ/GGUF/EXL2 delegation.

### `QuantizedModelWrapper`

Wraps an existing model and applies quantization by replacing `nn.Linear` layers.

### `FakeQuantize`

Simulates quantization noise for QAT.
