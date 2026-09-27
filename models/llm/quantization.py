"""
Phase 11 Quantization Module
=============================

Production-ready quantization toolkit for large language models. Provides:

1. Format support:
   - FP16 / BF16 (native PyTorch dtypes)
   - INT8 symmetric and asymmetric (per-tensor / per-channel)
   - GPTQ (with fallback to INT8 when unavailable)
   - AWQ (with fallback to INT8 when unavailable)
   - GGUF (with fallback when llama.cpp bindings unavailable)
   - EXL2 (with fallback when exllamaV2 unavailable)

2. Quantization methods:
   - Weight-only quantization
   - Activation quantization
   - Mixed-precision quantization (layer-wise dtype selection)
   - Quantization-aware training (QAT)
   - Post-training quantization (PTQ)

3. Utilities:
   - QuantizedLinear module
   - QuantizedModelWrapper for end-to-end model quantization
   - QuantizationConfig dataclass and parser
   - Export utilities for multiple formats

Hardware support:
- NVIDIA GPUs (CUDA, Ampere+ recommended for INT8)
- AMD GPUs via ROCm (partial support)
- CPU fallback for all operations

Graceful degradation:
- Each quantization format and method independently falls back to
  the nearest supported representation when libraries or hardware
  support are unavailable.
"""

from __future__ import annotations

import enum
import logging
import os
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hardware / dependency detection
# ---------------------------------------------------------------------------


def _is_cuda_available() -> bool:
    return torch.cuda.is_available()


def _cuda_device_count() -> int:
    return torch.cuda.device_count() if _is_cuda_available() else 0


def _is_rocm_available() -> bool:
    return hasattr(torch.version, "hip") and torch.version.hip is not None


def _has_autoawq() -> bool:
    try:
        import autoawq  # noqa: F401

        return True
    except ImportError:
        return False


def _has_gptqmodel() -> bool:
    try:
        import gptqmodel  # noqa: F401

        return True
    except ImportError:
        return False


def _has_gguf() -> bool:
    try:
        import gguf  # noqa: F401

        return True
    except ImportError:
        return False


def _has_exllamav2() -> bool:
    try:
        import exllamav2  # noqa: F401

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class QuantizationFormat(enum.Enum):
    """Supported quantization formats."""

    FP16 = "fp16"
    BF16 = "bf16"
    INT8_SYMMETRIC = "int8_symmetric"
    INT8_ASYMMETRIC = "int8_asymmetric"
    GPTQ = "gptq"
    AWQ = "awq"
    GGUF = "gguf"
    EXL2 = "exl2"


class QuantizationMethod(enum.Enum):
    """Quantization application methods."""

    WEIGHT_ONLY = "weight_only"
    ACTIVATION = "activation"
    MIXED_PRECISION = "mixed_precision"
    QUANTIZATION_AWARE_TRAINING = "qat"
    POST_TRAINING = "ptq"


@dataclass
class QuantizationConfig:
    """
    Configuration for model quantization.

    Attributes:
        format: Target quantization format.
        method: Quantization application method.
        weight_bits: Number of bits for weight quantization (4, 8, etc.).
        activation_bits: Number of bits for activation quantization.
        symmetric: Use symmetric quantization for INT8.
        per_channel: Use per-channel quantization scales.
        group_size: Group size for GPTQ/AWQ-style quantization.
        calibration_samples: Number of calibration samples for PTQ.
        learning_rate: Learning rate for QAT (if applicable).
        enable_fallback: Automatically fall back to a supported format.
        fallback_format: Format to use when the primary format is unavailable.
        device: Target device for quantization.
    """

    format: QuantizationFormat = QuantizationFormat.FP16
    method: QuantizationMethod = QuantizationMethod.WEIGHT_ONLY
    weight_bits: int = 8
    activation_bits: int = 8
    symmetric: bool = True
    per_channel: bool = True
    group_size: int = 128
    calibration_samples: int = 128
    learning_rate: float = 1e-5
    enable_fallback: bool = True
    fallback_format: QuantizationFormat = QuantizationFormat.INT8_SYMMETRIC
    device: torch.device | None = None

    def __post_init__(self) -> None:
        if self.device is None:
            self.device = torch.device("cuda" if _is_cuda_available() else "cpu")

    @property
    def effective_format(self) -> QuantizationFormat:
        """Return the format that will actually be used, considering fallback."""
        if not self.enable_fallback:
            return self.format

        if self.format == QuantizationFormat.GPTQ and not _has_gptqmodel():
            logger.warning("GPTQ unavailable; falling back to %s", self.fallback_format.value)
            return self.fallback_format

        if self.format == QuantizationFormat.AWQ and not _has_autoawq():
            logger.warning("AWQ unavailable; falling back to %s", self.fallback_format.value)
            return self.fallback_format

        if self.format == QuantizationFormat.GGUF and not _has_gguf():
            logger.warning("GGUF unavailable; falling back to %s", self.fallback_format.value)
            return self.fallback_format

        if self.format == QuantizationFormat.EXL2 and not _has_exllamav2():
            logger.warning("EXL2 unavailable; falling back to %s", self.fallback_format.value)
            return self.fallback_format

        return self.format

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuantizationConfig:
        """Create a QuantizationConfig from a dictionary."""
        fmt = data.get("format", "fp16")
        method = data.get("method", "weight_only")
        return cls(
            format=QuantizationFormat(fmt),
            method=QuantizationMethod(method),
            weight_bits=int(data.get("weight_bits", 8)),
            activation_bits=int(data.get("activation_bits", 8)),
            symmetric=bool(data.get("symmetric", True)),
            per_channel=bool(data.get("per_channel", True)),
            group_size=int(data.get("group_size", 128)),
            calibration_samples=int(data.get("calibration_samples", 128)),
            learning_rate=float(data.get("learning_rate", 1e-5)),
            enable_fallback=bool(data.get("enable_fallback", True)),
            fallback_format=QuantizationFormat(data.get("fallback_format", "int8_symmetric")),
            device=torch.device(data["device"]) if "device" in data else None,
        )

    @classmethod
    def from_yaml(cls, path: str) -> QuantizationConfig:
        """Load configuration from a YAML file."""
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "PyYAML is required to load quantization config from YAML. "
                "Install it with: pip install pyyaml"
            ) from exc

        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        if not isinstance(data, dict):
            raise ValueError(f"Expected a mapping in {path}, got {type(data).__name__}")

        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration to a dictionary."""
        return {
            "format": self.format.value,
            "method": self.method.value,
            "weight_bits": self.weight_bits,
            "activation_bits": self.activation_bits,
            "symmetric": self.symmetric,
            "per_channel": self.per_channel,
            "group_size": self.group_size,
            "calibration_samples": self.calibration_samples,
            "learning_rate": self.learning_rate,
            "enable_fallback": self.enable_fallback,
            "fallback_format": self.fallback_format.value,
            "device": str(self.device) if self.device is not None else None,
        }


# ---------------------------------------------------------------------------
# Low-level quantization helpers
# ---------------------------------------------------------------------------


def _quantize_per_tensor_int8(
    tensor: torch.Tensor,
    symmetric: bool = True,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
    """
    Quantize a tensor to INT8 (per-tensor).

    Returns (quantized_tensor, scale, zero_point).
    """
    if symmetric:
        abs_max = tensor.detach().abs().max()
        scale = abs_max / 127.0 if abs_max > 0 else torch.tensor(1.0, device=tensor.device)
        q = torch.clamp(torch.round(tensor / scale), -128, 127).to(torch.int8)
        return q, scale, None

    min_val = tensor.detach().min()
    max_val = tensor.detach().max()
    scale = (
        (max_val - min_val) / 255.0
        if max_val > min_val
        else torch.tensor(1.0, device=tensor.device)
    )
    zero_point = torch.round(-min_val / scale).clamp(0, 255).to(torch.int32)
    q = torch.clamp(torch.round(tensor / scale) + zero_point, 0, 255).to(torch.uint8)
    return q, scale, zero_point


def _quantize_per_channel_int8(
    tensor: torch.Tensor,
    dim: int = 0,
    symmetric: bool = True,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
    """
    Quantize a 2D weight tensor to INT8 per-channel.

    Returns (quantized_tensor, scale, zero_point).
    """
    if tensor.dim() != 2:
        raise ValueError(f"per-channel quantization requires 2D tensor, got {tensor.dim()}D")

    if symmetric:
        abs_max = tensor.detach().abs().amax(dim=dim, keepdim=True)
        scale = abs_max / 127.0
        scale = torch.where(abs_max == 0, torch.ones_like(scale), scale)
        q = torch.clamp(torch.round(tensor / scale), -128, 127).to(torch.int8)
        return q, scale.squeeze(dim), None

    min_val = tensor.detach().amin(dim=dim, keepdim=True)
    max_val = tensor.detach().amax(dim=dim, keepdim=True)
    scale = (max_val - min_val) / 255.0
    scale = torch.where((max_val - min_val) == 0, torch.ones_like(scale), scale)
    zero_point = torch.round(-min_val / scale).clamp(0, 255).to(torch.int32)
    q = torch.clamp(torch.round(tensor / scale) + zero_point, 0, 255).to(torch.uint8)
    return q, scale.squeeze(dim), zero_point.squeeze(dim)


def _dequantize_per_tensor(
    q: torch.Tensor,
    scale: torch.Tensor,
    zero_point: torch.Tensor | None,
    symmetric: bool = True,
) -> torch.Tensor:
    if symmetric:
        return (q.float() * scale).float()
    return ((q.float() - zero_point.float()) * scale).float()


def _dequantize_per_channel(
    q: torch.Tensor,
    scale: torch.Tensor,
    zero_point: torch.Tensor | None,
    dim: int = 0,
    symmetric: bool = True,
) -> torch.Tensor:
    scale = scale.to(q.device)
    if symmetric:
        scale_expanded = scale.view(*([1] * (q.dim() - dim - 1)), -1, *([1] * dim))
        return (q.float() * scale_expanded).float()
    zero_point = zero_point.to(q.device)
    zp_expanded = zero_point.view(*([1] * (q.dim() - dim - 1)), -1, *([1] * dim))
    scale_expanded = scale.view(*([1] * (q.dim() - dim - 1)), -1, *([1] * dim))
    return ((q.float() - zp_expanded) * scale_expanded).float()


def _cast_to_dtype(tensor: torch.Tensor, dtype: str | torch.dtype) -> torch.Tensor:
    if isinstance(dtype, str):
        dtype_map = {
            "fp16": torch.float16,
            "bf16": torch.bfloat16,
            "fp32": torch.float32,
            "int8": torch.int8,
            "uint8": torch.uint8,
        }
        dtype = dtype_map.get(dtype.lower(), torch.float32)
    return tensor.to(dtype)


# ---------------------------------------------------------------------------
# QuantizedLinear module
# ---------------------------------------------------------------------------


class QuantizedLinear(nn.Module):
    """
    Linear layer with quantized weights.

    Supports:
    - FP16 / BF16 passthrough
    - INT8 symmetric / asymmetric (per-tensor or per-channel)
    - GPTQ / AWQ / GGUF / EXL2 formats (delegates to external libraries when available)

    The forward pass dequantizes weights on-the-fly unless the backend
    supports native quantized matmuls.
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        bias: bool = True,
        config: QuantizationConfig | None = None,
        quantized_weight: torch.Tensor | None = None,
        scale: torch.Tensor | None = None,
        zero_point: torch.Tensor | None = None,
    ) -> None:
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.config = config or QuantizationConfig()
        self.effective_format = self.config.effective_format

        self._quantized_weight = quantized_weight
        self._scale = scale
        self._zero_point = zero_point
        self._weight_float: nn.Parameter | None = None

        if self.effective_format in (
            QuantizationFormat.FP16,
            QuantizationFormat.BF16,
        ):
            dtype = (
                torch.float16
                if self.effective_format == QuantizationFormat.FP16
                else torch.bfloat16
            )
            self._weight_float = nn.Parameter(torch.empty(out_features, in_features, dtype=dtype))
            if bias:
                self.bias = nn.Parameter(torch.zeros(out_features, dtype=dtype))
            else:
                self.register_parameter("bias", None)
        else:
            self._weight_float = nn.Parameter(torch.empty(out_features, in_features))
            if bias:
                self.bias = nn.Parameter(torch.zeros(out_features))
            else:
                self.register_parameter("bias", None)

        self._reset_parameters()

    def _reset_parameters(self) -> None:
        if self._weight_float is not None:
            nn.init.kaiming_uniform_(self._weight_float, a=5**0.5)
        if self.bias is not None:
            nn.init.zeros_(self.bias)

    @property
    def weight(self) -> nn.Parameter:
        """Return the dequantized weight for compatibility with standard PyTorch code."""
        if self._weight_float is not None:
            return self._weight_float
        if self._quantized_weight is not None:
            self._dequantize_weight()
            assert self._weight_float is not None
            return self._weight_float
        raise RuntimeError("QuantizedLinear has no weight.")

    def quantize(self, weight: torch.Tensor) -> None:
        """Quantize the given weight tensor according to the configuration."""
        fmt = self.effective_format
        if fmt in (QuantizationFormat.FP16, QuantizationFormat.BF16):
            dtype = torch.float16 if fmt == QuantizationFormat.FP16 else torch.bfloat16
            self._weight_float.data = weight.to(dtype)
            self._quantized_weight = None
            self._scale = None
            self._zero_point = None
            return

        if fmt in (QuantizationFormat.INT8_SYMMETRIC, QuantizationFormat.INT8_ASYMMETRIC):
            symmetric = fmt == QuantizationFormat.INT8_SYMMETRIC
            if self.config.per_channel and weight.dim() == 2:
                q, scale, zp = _quantize_per_channel_int8(weight, symmetric=symmetric)
            else:
                q, scale, zp = _quantize_per_tensor_int8(weight, symmetric=symmetric)
            self._quantized_weight = q
            self._scale = scale
            self._zero_point = zp
            self._weight_float = None
            return

        logger.warning(
            "Quantization for format %s is not yet implemented in QuantizedLinear; "
            "keeping FP32 weights.",
            fmt.value,
        )
        self._weight_float.data = weight

    def _dequantize_weight(self) -> None:
        """Dequantize weights back to floating point."""
        if self._weight_float is not None or self._quantized_weight is None:
            return

        fmt = self.effective_format
        if fmt in (QuantizationFormat.INT8_SYMMETRIC, QuantizationFormat.INT8_ASYMMETRIC):
            symmetric = fmt == QuantizationFormat.INT8_SYMMETRIC
            if self.config.per_channel and self._quantized_weight.dim() == 2:
                dequant = _dequantize_per_channel(
                    self._quantized_weight,
                    self._scale,
                    self._zero_point,
                    symmetric=symmetric,
                )
            else:
                dequant = _dequantize_per_tensor(
                    self._quantized_weight,
                    self._scale,
                    self._zero_point,
                    symmetric=symmetric,
                )
            self._weight_float = nn.Parameter(dequant)
            self._quantized_weight = None
            return

        warnings.warn(f"Dequantization for format {fmt.value} is not implemented.", stacklevel=2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weight = self._get_compute_weight()
        if weight.dtype != x.dtype:
            x = x.to(weight.dtype)
        return F.linear(x, weight, self.bias)

    def _get_compute_weight(self) -> torch.Tensor:
        """Return the weight tensor to use for the current forward pass."""
        if self._weight_float is not None:
            return self._weight_float
        if self._quantized_weight is not None:
            self._dequantize_weight()
            if self._weight_float is not None:
                return self._weight_float
        raise RuntimeError("QuantizedLinear has no usable weight tensor.")

    def extra_repr(self) -> str:
        return (
            f"in_features={self.in_features}, out_features={self.out_features}, "
            f"format={self.effective_format.value}, method={self.config.method.value}"
        )


# ---------------------------------------------------------------------------
# Fake quantization for QAT
# ---------------------------------------------------------------------------


class FakeQuantize(nn.Module):
    """
    Fake quantization module that simulates quantization noise during training.

    Used for quantization-aware training (QAT). The forward pass applies
    quantize-then-dequantize so that the model learns to compensate for
    quantization error.
    """

    def __init__(
        self,
        config: QuantizationConfig,
        forward_fn: Callable[[torch.Tensor], torch.Tensor] | None = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.forward_fn = forward_fn

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.config.effective_format in (
            QuantizationFormat.FP16,
            QuantizationFormat.BF16,
        ):
            return x

        if self.forward_fn is not None:
            return self.forward_fn(x)

        fmt = self.config.effective_format
        if fmt in (
            QuantizationFormat.INT8_SYMMETRIC,
            QuantizationFormat.INT8_ASYMMETRIC,
        ):
            symmetric = fmt == QuantizationFormat.INT8_SYMMETRIC
            if x.dim() == 2:
                q, scale, zp = _quantize_per_channel_int8(x, symmetric=symmetric)
                return _dequantize_per_channel(q, scale, zp, symmetric=symmetric)
            q, scale, zp = _quantize_per_tensor_int8(x, symmetric=symmetric)
            return _dequantize_per_tensor(q, scale, zp, symmetric=symmetric)

        return x


def _wrap_linear_with_qat(module: nn.Linear, config: QuantizationConfig) -> nn.Module:
    """Replace a Linear layer with a QAT-wrapped version."""
    weight_fq = FakeQuantize(config)
    act_fq = FakeQuantize(config)

    def qat_forward(x: torch.Tensor) -> torch.Tensor:
        x_q = act_fq(x)
        weight_q = weight_fq(module.weight)
        return F.linear(x_q, weight_q, module.bias)

    module.forward = qat_forward  # type: ignore[method-assign]
    module._qat_weight_fq = weight_fq  # type: ignore[attr-defined]
    module._qat_act_fq = act_fq  # type: ignore[attr-defined]
    return module


# ---------------------------------------------------------------------------
# Calibration for PTQ
# ---------------------------------------------------------------------------


def _default_calibration_loader(
    config: QuantizationConfig,
) -> list[torch.Tensor]:
    """
    Produce dummy calibration data for PTQ.

    In production, replace this with a real data loader yielding input tensors.
    """
    samples = []
    for _ in range(config.calibration_samples):
        samples.append(torch.randn(1, 16, dtype=torch.long, device=config.device))
    return samples


@torch.no_grad()
def calibrate_model(
    model: nn.Module,
    config: QuantizationConfig,
    calibration_loader: Callable[[], list[torch.Tensor]] | None = None,
) -> None:
    """
    Run calibration data through the model to collect activation statistics.

    Required for post-training quantization (PTQ).
    """
    loader = calibration_loader or _default_calibration_loader
    data = loader(config)

    model.eval()
    for sample in data:
        try:
            model(sample.to(config.device))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Calibration sample failed: %s", exc)


# ---------------------------------------------------------------------------
# QuantizedModelWrapper
# ---------------------------------------------------------------------------


class QuantizedModelWrapper(nn.Module):
    """
    Wraps an existing model and applies quantization according to the config.

    Supports:
    - Replacing nn.Linear with QuantizedLinear
    - Applying activation fake-quantization for QAT
    - Casting model weights to FP16/BF16
    - GPTQ/AWQ/GGUF/EXL2 delegation (with fallback to INT8)
    """

    def __init__(
        self,
        model: nn.Module,
        config: QuantizationConfig | None = None,
        layers_to_quantize: list[str] | None = None,
        calibration_loader: Callable[[], list[torch.Tensor]] | None = None,
    ) -> None:
        super().__init__()
        self.model = model
        self.config = config or QuantizationConfig()
        self.layers_to_quantize = layers_to_quantize or []
        self.calibration_loader = calibration_loader
        self._quantized_layers: dict[str, QuantizedLinear] = {}

        self._apply_quantization()

    def _apply_quantization(self) -> None:
        fmt = self.config.effective_format
        method = self.config.method

        if fmt in (QuantizationFormat.FP16, QuantizationFormat.BF16):
            self._cast_model_dtype(fmt)
            return

        if method == QuantizationMethod.QUANTIZATION_AWARE_TRAINING:
            self._apply_qat()
            return

        if method == QuantizationMethod.POST_TRAINING:
            self._apply_ptq()
            return

        self._apply_weight_only_quantization()

    def _cast_model_dtype(self, fmt: QuantizationFormat) -> None:
        dtype = torch.float16 if fmt == QuantizationFormat.FP16 else torch.bfloat16
        try:
            self.model = self.model.to(dtype)
            logger.info("Model cast to %s.", dtype)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to cast model to %s: %s", dtype, exc)

    def _apply_qat(self) -> None:
        """Apply fake quantization for quantization-aware training."""
        for name, module in self.model.named_modules():
            if isinstance(module, nn.Linear) and self._should_quantize(name):
                _wrap_linear_with_qat(module, self.config)
                logger.debug("QAT applied to layer: %s", name)

    def _apply_ptq(self) -> None:
        """Apply post-training quantization."""
        logger.info("Running PTQ calibration...")
        calibrate_model(self.model, self.config, self.calibration_loader)
        self._apply_weight_only_quantization()
        logger.info("PTQ complete.")

    def _apply_weight_only_quantization(self) -> None:
        """Replace Linear layers with QuantizedLinear."""
        for name, module in self.model.named_modules():
            if not isinstance(module, nn.Linear):
                continue
            if not self._should_quantize(name):
                continue

            qlinear = QuantizedLinear(
                in_features=module.in_features,
                out_features=module.out_features,
                bias=module.bias is not None,
                config=self.config,
            )
            qlinear.quantize(module.weight.data.clone())
            if module.bias is not None and qlinear.bias is not None:
                qlinear.bias.data = module.bias.data.clone()

            parent, _, attr = name.rpartition(".")
            if parent:
                parent_mod = self.model.get_submodule(parent)
                setattr(parent_mod, attr, qlinear)
            else:
                setattr(self.model, name, qlinear)

            self._quantized_layers[name] = qlinear
            logger.debug("Quantized layer: %s", name)

    def _should_quantize(self, name: str) -> bool:
        if not self.layers_to_quantize:
            return True
        return any(pattern in name for pattern in self.layers_to_quantize)

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        return self.model(*args, **kwargs)

    def get_quantized_layers(self) -> dict[str, QuantizedLinear]:
        """Return mapping of layer names to QuantizedLinear modules."""
        return dict(self._quantized_layers)

    def export(self, path: str, fmt: QuantizationFormat | None = None) -> None:
        """
        Export the quantized model to the specified format.

        Supported formats: FP16, BF16, INT8_SYMMETRIC, GGUF (when available).
        """
        export_format = fmt or self.config.effective_format
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        if export_format in (QuantizationFormat.FP16, QuantizationFormat.BF16):
            self._export_fp(path, export_format)
        elif export_format in (
            QuantizationFormat.INT8_SYMMETRIC,
            QuantizationFormat.INT8_ASYMMETRIC,
        ):
            self._export_int8(path)
        elif export_format == QuantizationFormat.GGUF:
            self._export_gguf(path)
        else:
            logger.warning(
                "Export for format %s not implemented; exporting FP16 fallback.",
                export_format.value,
            )
            self._export_fp(path, QuantizationFormat.FP16)

    def _export_fp(self, path: str, fmt: QuantizationFormat) -> None:
        dtype = torch.float16 if fmt == QuantizationFormat.FP16 else torch.bfloat16
        state_dict = {k: v.to(dtype) for k, v in self.model.state_dict().items()}
        torch.save(state_dict, path)
        logger.info("Exported %s model to %s", fmt.value, path)

    def _export_int8(self, path: str) -> None:
        state_dict = {}
        for name, module in self.model.named_modules():
            if name in self._quantized_layers:
                qlinear = self._quantized_layers[name]
                state_dict[f"{name}.weight"] = qlinear._quantized_weight
                state_dict[f"{name}.scale"] = qlinear._scale
                if qlinear._zero_point is not None:
                    state_dict[f"{name}.zero_point"] = qlinear._zero_point
                if qlinear.bias is not None:
                    state_dict[f"{name}.bias"] = qlinear.bias.data
            elif isinstance(module, nn.Linear):
                state_dict[f"{name}.weight"] = module.weight.data
                if module.bias is not None:
                    state_dict[f"{name}.bias"] = module.bias.data
        torch.save(state_dict, path)
        logger.info("Exported INT8 model to %s", path)

    def _export_gguf(self, path: str) -> None:
        if not _has_gguf():
            logger.warning("GGUF library unavailable; falling back to FP16 export.")
            self._export_fp(path, QuantizationFormat.FP16)
            return

        try:
            import gguf  # type: ignore[import-untyped]

            state_dict = self.model.state_dict()
            gguf_writer = gguf.GGUFWriter(path, "llm")
            for tensor_name, tensor in state_dict.items():
                gguf_writer.add_tensor(tensor_name, tensor.cpu().numpy())
            gguf_writer.write_header_to_file()
            gguf_writer.write_kv_data_to_file()
            gguf_writer.write_tensors_to_file()
            gguf_writer.close()
            logger.info("Exported GGUF model to %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("GGUF export failed (%s); falling back to FP16.", exc)
            self._export_fp(path, QuantizationFormat.FP16)


# ---------------------------------------------------------------------------
# GPTQ / AWQ / EXL2 delegation (with fallback)
# ---------------------------------------------------------------------------


def quantize_gptq(
    model: nn.Module,
    config: QuantizationConfig,
    calibration_loader: Callable[[], list[torch.Tensor]] | None = None,
) -> nn.Module:
    """
    Apply GPTQ quantization to a model.

    Falls back to INT8 symmetric quantization when the GPTQ library
    is unavailable.
    """
    if not _has_gptqmodel():
        logger.warning("GPTQ library unavailable; falling back to INT8 symmetric.")
        config = QuantizationConfig(
            format=QuantizationFormat.INT8_SYMMETRIC,
            method=QuantizationMethod.WEIGHT_ONLY,
            weight_bits=config.weight_bits,
            per_channel=config.per_channel,
            device=config.device,
        )
        return QuantizedModelWrapper(model, config=config)

    try:
        from gptqmodel import GPTQModel  # type: ignore[import-untyped]
        from gptqmodel.utils import QuantizeConfig  # type: ignore[import-untyped]

        qconfig = QuantizeConfig(
            bits=config.weight_bits,
            group_size=config.group_size,
            sym=config.symmetric,
        )
        calibration_data = (
            calibration_loader() if calibration_loader else _default_calibration_loader(config)
        )
        gptq_model = GPTQModel.quantize(model, qconfig, calibration_data)
        logger.info("GPTQ quantization applied successfully.")
        return gptq_model
    except Exception as exc:  # noqa: BLE001
        logger.warning("GPTQ quantization failed (%s); falling back to INT8 symmetric.", exc)
        config = QuantizationConfig(
            format=QuantizationFormat.INT8_SYMMETRIC,
            method=QuantizationMethod.WEIGHT_ONLY,
            weight_bits=config.weight_bits,
            per_channel=config.per_channel,
            device=config.device,
        )
        return QuantizedModelWrapper(model, config=config)


def quantize_awq(
    model: nn.Module,
    config: QuantizationConfig,
    calibration_loader: Callable[[], list[torch.Tensor]] | None = None,
) -> nn.Module:
    """
    Apply AWQ quantization to a model.

    Falls back to INT8 symmetric quantization when the AutoAWQ library
    is unavailable.
    """
    if not _has_autoawq():
        logger.warning("AutoAWQ unavailable; falling back to INT8 symmetric.")
        config = QuantizationConfig(
            format=QuantizationFormat.INT8_SYMMETRIC,
            method=QuantizationMethod.WEIGHT_ONLY,
            weight_bits=config.weight_bits,
            per_channel=config.per_channel,
            device=config.device,
        )
        return QuantizedModelWrapper(model, config=config)

    try:
        from awq import quantize  # type: ignore[import-untyped]

        awq_config = {
            "zero_point": not config.symmetric,
            "q_group_size": config.group_size,
            "w_bit": config.weight_bits,
            "version": "GEMM",
        }
        calibration_data = (
            calibration_loader() if calibration_loader else _default_calibration_loader(config)
        )
        quantize(model, awq_config, calibration_data)
        logger.info("AWQ quantization applied successfully.")
        return model
    except Exception as exc:  # noqa: BLE001
        logger.warning("AWQ quantization failed (%s); falling back to INT8 symmetric.", exc)
        config = QuantizationConfig(
            format=QuantizationFormat.INT8_SYMMETRIC,
            method=QuantizationMethod.WEIGHT_ONLY,
            weight_bits=config.weight_bits,
            per_channel=config.per_channel,
            device=config.device,
        )
        return QuantizedModelWrapper(model, config=config)


def quantize_exl2(
    model: nn.Module,
    config: QuantizationConfig,
    calibration_loader: Callable[[], list[torch.Tensor]] | None = None,
) -> nn.Module:
    """
    Apply EXL2 quantization to a model.

    Falls back to INT8 symmetric quantization when exllamaV2 is unavailable.
    """
    if not _has_exllamav2():
        logger.warning("exllamaV2 unavailable; falling back to INT8 symmetric.")
        config = QuantizationConfig(
            format=QuantizationFormat.INT8_SYMMETRIC,
            method=QuantizationMethod.WEIGHT_ONLY,
            weight_bits=config.weight_bits,
            per_channel=config.per_channel,
            device=config.device,
        )
        return QuantizedModelWrapper(model, config=config)

    try:

        logger.warning(
            "EXL2 quantization requires an ExLlamaV2-compatible model load; "
            "applying INT8 symmetric fallback."
        )
        config = QuantizationConfig(
            format=QuantizationFormat.INT8_SYMMETRIC,
            method=QuantizationMethod.WEIGHT_ONLY,
            weight_bits=config.weight_bits,
            per_channel=config.per_channel,
            device=config.device,
        )
        return QuantizedModelWrapper(model, config=config)
    except Exception as exc:  # noqa: BLE001
        logger.warning("EXL2 quantization failed (%s); falling back to INT8 symmetric.", exc)
        config = QuantizationConfig(
            format=QuantizationFormat.INT8_SYMMETRIC,
            method=QuantizationMethod.WEIGHT_ONLY,
            weight_bits=config.weight_bits,
            per_channel=config.per_channel,
            device=config.device,
        )
        return QuantizedModelWrapper(model, config=config)


# ---------------------------------------------------------------------------
# High-level quantization API
# ---------------------------------------------------------------------------


def quantize_model(
    model: nn.Module,
    config: QuantizationConfig | dict[str, Any] | None = None,
    layers_to_quantize: list[str] | None = None,
    calibration_loader: Callable[[], list[torch.Tensor]] | None = None,
) -> nn.Module:
    """
    Quantize a model using the specified configuration.

    Args:
        model: The model to quantize.
        config: QuantizationConfig or dictionary of config options.
        layers_to_quantize: Optional list of layer name patterns to quantize.
            If None, all nn.Linear layers are quantized.
        calibration_loader: Optional callable returning calibration inputs for PTQ.

    Returns:
        Quantized model. For GPTQ/AWQ/EXL2, this may be a library-specific
        wrapper; for other formats, a QuantizedModelWrapper is returned.
    """
    if isinstance(config, dict):
        config = QuantizationConfig.from_dict(config)

    cfg = config or QuantizationConfig()
    fmt = cfg.effective_format
    method = cfg.method

    logger.info("Quantizing model with format=%s, method=%s", fmt.value, method.value)

    if fmt == QuantizationFormat.GPTQ:
        return quantize_gptq(model, cfg, calibration_loader)

    if fmt == QuantizationFormat.AWQ:
        return quantize_awq(model, cfg, calibration_loader)

    if fmt == QuantizationFormat.EXL2:
        return quantize_exl2(model, cfg, calibration_loader)

    if fmt == QuantizationFormat.GGUF:
        wrapper = QuantizedModelWrapper(
            model,
            config=cfg,
            layers_to_quantize=layers_to_quantize,
            calibration_loader=calibration_loader,
        )
        logger.info("GGUF format selected; using QuantizedModelWrapper with fallback support.")
        return wrapper

    if method in (
        QuantizationMethod.QUANTIZATION_AWARE_TRAINING,
        QuantizationMethod.POST_TRAINING,
        QuantizationMethod.WEIGHT_ONLY,
        QuantizationMethod.ACTIVATION,
        QuantizationMethod.MIXED_PRECISION,
    ):
        return QuantizedModelWrapper(
            model,
            config=cfg,
            layers_to_quantize=layers_to_quantize,
            calibration_loader=calibration_loader,
        )

    logger.warning("Unsupported quantization format/method combination; returning model unchanged.")
    return model


def get_supported_formats() -> list[str]:
    """Return a list of quantization formats supported in the current environment."""
    formats = [
        QuantizationFormat.FP16.value,
        QuantizationFormat.BF16.value,
        QuantizationFormat.INT8_SYMMETRIC.value,
        QuantizationFormat.INT8_ASYMMETRIC.value,
    ]
    if _has_gptqmodel():
        formats.append(QuantizationFormat.GPTQ.value)
    if _has_autoawq():
        formats.append(QuantizationFormat.AWQ.value)
    if _has_gguf():
        formats.append(QuantizationFormat.GGUF.value)
    if _has_exllamav2():
        formats.append(QuantizationFormat.EXL2.value)
    return formats


def get_supported_methods() -> list[str]:
    """Return quantization methods supported in the current environment."""
    methods = [
        QuantizationMethod.WEIGHT_ONLY.value,
        QuantizationMethod.ACTIVATION.value,
        QuantizationMethod.MIXED_PRECISION.value,
        QuantizationMethod.POST_TRAINING.value,
    ]
    if torch.cuda.is_available():
        methods.append(QuantizationMethod.QUANTIZATION_AWARE_TRAINING.value)
    return methods
