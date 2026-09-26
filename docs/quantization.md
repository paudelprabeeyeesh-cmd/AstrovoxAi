# Quantization Guide

AstrovoxAI supports multiple quantization methods for compressing models and reducing inference latency.

## Supported Methods
- **INT8 Quantization**: Dynamic and static quantization for CPUs
- **FP8 Quantization**: 8-bit floating point for GPUs (H100, A100)
- **FP4 Quantization**: 4-bit floating point for extreme compression
- **NF4 Quantization**: 4-bit normal-float for LLM weights
- **GPTQ**: Post-training 4-bit quantization with group-wise scaling
- **AWQ**: Activation-aware quantization for LLMs
- **E8M0**: Exponent-only quantization for outlier-free weights

## Usage
```python
from ASTROVOX_AI.ai_core.quantization.gptq import GPTQQuantizer
from ASTROVOX_AI.ai_core.quantization.int8_quantization import INT8Quantizer

# GPTQ 4-bit
quantizer = GPTQQuantizer(bits=4, group_size=128)
quantized_model = quantizer.quantize_model(model)

# INT8
int8_quantizer = INT8Quantizer()
quantized_model = int8_quantizer.quantize_model(model)
```

## Performance
| Method | Bits | Accuracy Drop | Speedup |
|--------|------|---------------|---------|
| FP16   | 16   | 0%            | 1x      |
| INT8   | 8    | 0.1-0.5%      | 1.5-2x  |
| GPTQ   | 4    | 0.5-1.5%      | 2-3x    |
| NF4    | 4    | 0.3-1.0%      | 2-3x    |
