import logging
from dataclasses import dataclass
from typing import Optional
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class QuantizationResult:
    method: str
    model_size_mb: float
    accuracy: float
    latency_ms: float
    bits: int


class QuantizationEvaluator:
    def __init__(self, model: nn.Module, dummy_input: torch.Tensor):
        self.model = model
        self.dummy_input = dummy_input

    @torch.no_grad()
    def _measure_latency(self, model: nn.Module, repeats: int = 50) -> float:
        latencies = []
        for _ in range(repeats):
            start = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            end = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            if torch.cuda.is_available():
                start.record()
                _ = model(self.dummy_input)
                end.record()
                torch.cuda.synchronize()
                latencies.append(start.elapsed_time(end))
            else:
                import time
                start_time = time.perf_counter()
                _ = model(self.dummy_input)
                latencies.append((time.perf_counter() - start_time) * 1000)
        return sum(latencies) / len(latencies)

    def _model_size_mb(self, model: nn.Module) -> float:
        param_size = 0
        for param in model.parameters():
            param_size += param.nelement() * param.element_size()
        buffer_size = 0
        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()
        return (param_size + buffer_size) / (1024 * 1024)

    def evaluate_fp32(self) -> QuantizationResult:
        latency = self._measure_latency(self.model)
        return QuantizationResult(
            method="fp32",
            model_size_mb=self._model_size_mb(self.model),
            accuracy=0.0,
            latency_ms=latency,
            bits=32,
        )

    def evaluate_dynamic_quant(self) -> QuantizationResult:
        try:
            quantized = torch.quantization.quantize_dynamic(self.model, {nn.Linear}, dtype=torch.qint8)
        except Exception as exc:
            logger.warning("Dynamic quantization failed: %s", exc)
            return QuantizationResult(method="dynamic_quant", model_size_mb=0.0, accuracy=0.0, latency_ms=0.0, bits=8)
        latency = self._measure_latency(quantized)
        return QuantizationResult(
            method="dynamic_quant",
            model_size_mb=self._model_size_mb(quantized),
            accuracy=0.0,
            latency_ms=latency,
            bits=8,
        )

    def run(self) -> None:
        fp32 = self.evaluate_fp32()
        dq = self.evaluate_dynamic_quant()
        for result in (fp32, dq):
            logger.info(
                "%s: size=%.2fMB bits=%d latency=%.3fms accuracy=%.4f",
                result.method,
                result.model_size_mb,
                result.bits,
                result.latency_ms,
                result.accuracy,
            )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    model = nn.Linear(768, 768)
    dummy = torch.randn(1, 768)
    QuantizationEvaluator(model, dummy).run()
