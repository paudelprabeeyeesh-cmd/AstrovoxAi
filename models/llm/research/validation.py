from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    benchmark: str
    score: float
    baseline_score: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class LatencyMeasurement:
    component: str
    mean_ms: float
    p95_ms: float
    p99_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class MemoryMeasurement:
    component: str
    peak_mb: float
    allocated_mb: float
    reserved_mb: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class AblationConfig:
    name: str
    use_attention: bool = True
    use_feedforward: bool = True
    use_norm: bool = True
    num_layers: int = 2


@dataclass
class AblationResult:
    config: AblationConfig
    score: float
    params: int
    latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class ValidationReport:
    experiment_id: str
    benchmark_results: List[BenchmarkResult]
    latency_measurements: List[LatencyMeasurement]
    memory_measurements: List[MemoryMeasurement]
    ablation_results: List[AblationResult]
    reproducibility_score: float
    rollback_plan_id: str
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class BenchmarkTracker:
    def __init__(self, baseline_dir: str = "baselines"):
        self.baseline_dir = baseline_dir
        self.results: List[BenchmarkResult] = []

    def record(self, benchmark: str, score: float, baseline_score: float, unit: str) -> BenchmarkResult:
        result = BenchmarkResult(benchmark=benchmark, score=score, baseline_score=baseline_score, unit=unit)
        self.results.append(result)
        improvement = ((score - baseline_score) / baseline_score) * 100 if baseline_score != 0 else 0
        logger.info("Benchmark %s: %.2f %s (baseline %.2f, improvement %.1f%%)", benchmark, score, unit, baseline_score, improvement)
        return result

    def summary(self) -> Dict:
        return {
            "benchmarks": [
                {
                    "benchmark": r.benchmark,
                    "score": r.score,
                    "baseline_score": r.baseline_score,
                    "unit": r.unit,
                    "improvement": ((r.score - r.baseline_score) / r.baseline_score) * 100 if r.baseline_score != 0 else 0,
                    "timestamp": r.timestamp,
                }
                for r in self.results
            ]
        }


class LatencyImpactMeasurer:
    def __init__(self):
        self.measurements: List[LatencyMeasurement] = []

    def record(self, component: str, mean_ms: float, p95_ms: float, p99_ms: float) -> LatencyMeasurement:
        measurement = LatencyMeasurement(component=component, mean_ms=mean_ms, p95_ms=p95_ms, p99_ms=p99_ms)
        self.measurements.append(measurement)
        logger.info("Latency %s: mean=%.2fms p95=%.2fms p99=%.2fms", component, mean_ms, p95_ms, p99_ms)
        return measurement

    def summary(self) -> Dict:
        return {
            "latency": [
                {
                    "component": m.component,
                    "mean_ms": m.mean_ms,
                    "p95_ms": m.p95_ms,
                    "p99_ms": m.p99_ms,
                    "timestamp": m.timestamp,
                }
                for m in self.measurements
            ]
        }


class MemoryImpactMeasurer:
    def __init__(self):
        self.measurements: List[MemoryMeasurement] = []

    def record(self, component: str, peak_mb: float, allocated_mb: float, reserved_mb: float) -> MemoryMeasurement:
        measurement = MemoryMeasurement(component=component, peak_mb=peak_mb, allocated_mb=allocated_mb, reserved_mb=reserved_mb)
        self.measurements.append(measurement)
        logger.info("Memory %s: peak=%.1fMB allocated=%.1fMB reserved=%.1fMB", component, peak_mb, allocated_mb, reserved_mb)
        return measurement

    def summary(self) -> Dict:
        return {
            "memory": [
                {
                    "component": m.component,
                    "peak_mb": m.peak_mb,
                    "allocated_mb": m.allocated_mb,
                    "reserved_mb": m.reserved_mb,
                    "timestamp": m.timestamp,
                }
                for m in self.measurements
            ]
        }


class AblationStudyRunner:
    def __init__(self, input_dim: int = 64, hidden_size: int = 128, seq_len: int = 32, vocab_size: int = 100):
        self.input_dim = input_dim
        self.hidden_size = hidden_size
        self.seq_len = seq_len
        self.vocab_size = vocab_size

    def _build_model(self, config: AblationConfig) -> torch.nn.Module:
        import torch.nn as nn
        layers: List[nn.Module] = []
        for _ in range(max(1, config.num_layers)):
            if config.use_norm:
                layers.append(nn.LayerNorm(self.hidden_size))
            if config.use_attention:
                layers.append(nn.MultiheadAttention(self.hidden_size, 4, batch_first=True))
            if config.use_feedforward:
                layers.append(nn.Sequential(nn.Linear(self.hidden_size, self.hidden_size * 4), nn.GELU(), nn.Linear(self.hidden_size * 4, self.hidden_size)))
        return nn.Sequential(nn.Linear(self.input_dim, self.hidden_size), *layers, nn.Linear(self.hidden_size, self.vocab_size))

    def _count_params(self, model: torch.nn.Module) -> int:
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    def _estimate_latency(self, model: torch.nn.Module, x: torch.Tensor) -> float:
        import time
        model.eval()
        with torch.no_grad():
            for _ in range(5):
                _ = model(x)
        start = time.perf_counter()
        with torch.no_grad():
            for _ in range(20):
                _ = model(x)
        end = time.perf_counter()
        return ((end - start) / 20) * 1000

    def _estimate_score(self, model: torch.nn.Module, x: torch.Tensor) -> float:
        with torch.no_grad():
            out = model(x)
            target = torch.zeros(x.size(0), x.size(1), dtype=torch.long, device=x.device)
            loss = torch.nn.functional.cross_entropy(out.transpose(1, 2), target)
        return loss.item()

    def run(self, configs: Optional[List[AblationConfig]] = None) -> List[AblationResult]:
        import torch
        if configs is None:
            configs = [
                AblationConfig("full"),
                AblationConfig("no_ffn", use_feedforward=False),
                AblationConfig("no_attn", use_attention=False),
                AblationConfig("no_norm", use_norm=False),
                AblationConfig("shallow", num_layers=1),
            ]
        x = torch.randn(2, self.seq_len, self.input_dim)
        results: List[AblationResult] = []
        for config in configs:
            model = self._build_model(config)
            params = self._count_params(model)
            score = self._estimate_score(model, x)
            latency = self._estimate_latency(model, x)
            results.append(AblationResult(config=config, score=score, params=params, latency_ms=latency))
            logger.info("Ablation %s: params=%d score=%.4f latency=%.2fms", config.name, params, score, latency)
        return results


class ReproducibilityChecker:
    def __init__(self):
        self.hardware_info: Dict = {}
        self.software_info: Dict = {}
        self.seed_state: Dict = {}

    def detect_hardware(self) -> Dict:
        import torch
        cpu_info = {"device": torch.cpu.get_device_name() if hasattr(torch.cpu, "get_device_name") else "unknown"}
        cuda_info = {"available": torch.cuda.is_available(), "count": torch.cuda.device_count(), "name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "n/a"}
        mps_info = {"available": torch.mps.is_available(), "device": torch.mps.current_device() if torch.mps.is_available() else "n/a"}
        self.hardware_info = {"cpu": cpu_info, "cuda": cuda_info, "mps": mps_info}
        logger.info("Hardware detected: %s", self.hardware_info)
        return self.hardware_info

    def detect_environment(self) -> Dict:
        import platform
        import sys
        import torch
        self.software_info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "torch_version": torch.__version__,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        logger.info("Environment detected: %s", self.software_info)
        return self.software_info

    def set_seed(self, seed: int) -> Dict:
        import torch
        import numpy as np
        import random
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if torch.mps.is_available():
            torch.mps.manual_seed(seed)
        self.seed_state = {"seed": seed, "python_seed": seed, "numpy_seed": seed, "torch_seed": seed}
        logger.info("Seed set to %d", seed)
        return self.seed_state

    def compare_results(self, result_a: Dict, result_b: Dict, tolerance: float = 1e-5) -> Dict:
        differences = {}
        for key in set(result_a) | set(result_b):
            val_a = result_a.get(key)
            val_b = result_b.get(key)
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                diff = abs(val_a - val_b)
                if diff > tolerance:
                    differences[key] = {"a": val_a, "b": val_b, "diff": diff}
        report = {"similar": len(differences) == 0, "differences": differences, "tolerance": tolerance}
        logger.info("Result comparison: %s", report)
        return report

    def snapshot(self) -> Dict:
        self.detect_hardware()
        self.detect_environment()
        return {"hardware": self.hardware_info, "software": self.software_info, "seed": self.seed_state}


class ValidationFramework:
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.benchmark_tracker = BenchmarkTracker()
        self.latency_measurer = LatencyImpactMeasurer()
        self.memory_measurer = MemoryImpactMeasurer()
        self.ablation_runner = AblationStudyRunner()
        self.reproducibility_checker = ReproducibilityChecker()
        self.rollback_plan_id: str = ""

    def set_rollback_plan(self, plan_id: str) -> None:
        self.rollback_plan_id = plan_id
        logger.info("Rollback plan set to %s", plan_id)

    def validate(self, ablation_configs: Optional[List[AblationConfig]] = None) -> ValidationReport:
        ablation_results = self.ablation_runner.run(ablation_configs)
        repro_score = 1.0
        return ValidationReport(
            experiment_id=self.experiment_id,
            benchmark_results=self.benchmark_tracker.results,
            latency_measurements=self.latency_measurer.measurements,
            memory_measurements=self.memory_measurer.measurements,
            ablation_results=ablation_results,
            reproducibility_score=repro_score,
            rollback_plan_id=self.rollback_plan_id,
        )

    def report(self) -> Dict:
        return {
            "experiment_id": self.experiment_id,
            "benchmarks": self.benchmark_tracker.summary(),
            "latency": self.latency_measurer.summary(),
            "memory": self.memory_measurer.summary(),
            "ablation": [{"name": r.config.name, "score": r.score, "params": r.params, "latency_ms": r.latency_ms} for r in self.ablation_runner.run()],
            "rollback_plan_id": self.rollback_plan_id,
        }
