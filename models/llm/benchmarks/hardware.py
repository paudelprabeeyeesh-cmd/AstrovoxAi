from __future__ import annotations

import dataclasses
import math
import os
import platform
import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from models.llm.benchmarking import BenchmarkRun, BenchmarkSuite, SystemMonitor


@dataclasses.dataclass
class HardwareProfile:
    vendor: str
    name: str
    device_type: str
    memory_gb: float = 0.0
    compute_capability: str = ""
    bandwidth_gb_per_s: float = 0.0
    peak_tflops: float = 0.0
    power_watts: float = 0.0
    cost_per_hour: float = 0.0
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclass
class BenchmarkResult:
    name: str
    metrics: Dict[str, Any]
    profile: Optional[HardwareProfile] = None
    timestamp: str = ""


class NvidiaBenchmark:
    def __init__(self, profile: HardwareProfile) -> None:
        self.profile = profile

    def inference_benchmark(self, model, tokenizer, prompts: List[str], max_new_tokens: int = 32, device: str = "cuda") -> BenchmarkResult:
        if model is None:
            metrics = {
                "vendor": "nvidia",
                "status": "stub",
                "message": "No model provided for benchmarking",
                "num_prompts": len(prompts),
                "max_new_tokens": max_new_tokens,
                "avg_latency_seconds": 0.0,
                "avg_tokens_per_second": 0.0,
                "p50_latency_seconds": 0.0,
                "p95_latency_seconds": 0.0,
                "p99_latency_seconds": 0.0,
            }
            return BenchmarkResult(
                name=f"nvidia_inference_{self.profile.name}",
                metrics=metrics,
                profile=self.profile,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        from models.llm.inference.engine import InferenceEngine, SamplingParams

        engine = InferenceEngine(model, tokenizer, device=device)
        params = SamplingParams(max_new_tokens=max_new_tokens, temperature=1.0)
        latencies = []
        tokens_per_sec = []

        monitor = SystemMonitor(interval=0.5)
        monitor.start()
        for prompt in prompts:
            start = time.perf_counter()
            output = engine.generate(prompt, params)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            tps = output.num_tokens / elapsed if elapsed > 0 else 0.0
            tokens_per_sec.append(tps)
        monitor.stop()

        sorted_latencies = sorted(latencies)
        n = len(latencies)
        metrics = {
            "vendor": "nvidia",
            "num_prompts": len(prompts),
            "max_new_tokens": max_new_tokens,
            "latencies_seconds": latencies,
            "tokens_per_second": tokens_per_sec,
            "avg_latency_seconds": round(sum(latencies) / len(latencies), 4) if latencies else 0.0,
            "avg_tokens_per_second": round(sum(tokens_per_sec) / len(tokens_per_sec), 4) if tokens_per_sec else 0.0,
            "p50_latency_seconds": round(sorted_latencies[n // 2], 4) if n else 0.0,
            "p95_latency_seconds": round(sorted_latencies[int(n * 0.95)], 4) if n else 0.0,
            "p99_latency_seconds": round(sorted_latencies[int(n * 0.99)], 4) if n else 0.0,
            "gpu_utilization_avg_percent": self._avg_from_samples(monitor, "gpu_utilization_percent"),
            "gpu_memory_avg_mb": self._avg_from_samples(monitor, "gpu_memory_mb"),
        }

        return BenchmarkResult(
            name=f"nvidia_inference_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def training_benchmark(self, model, config: Dict[str, Any], steps: int = 5, device: str = "cuda") -> BenchmarkResult:
        if model is None:
            metrics = {
                "vendor": "nvidia",
                "status": "stub",
                "message": "No model provided for benchmarking",
                "steps": steps,
                "avg_step_time_seconds": 0.0,
                "tokens_per_second": 0.0,
                "total_tokens_per_step": config["batch_size"] * config.get("max_position_embeddings", 1024),
            }
            return BenchmarkResult(
                name=f"nvidia_training_{self.profile.name}",
                metrics=metrics,
                profile=self.profile,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        import torch

        model.train()
        dummy_input = torch.randint(
            0,
            config["vocab_size"],
            (config["batch_size"], config.get("max_position_embeddings", 1024)),
            device=device,
        )
        dummy_labels = dummy_input.clone()
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)

        monitor = SystemMonitor(interval=0.5)
        monitor.start()
        times = []
        for _ in range(steps):
            if device == "cuda":
                torch.cuda.synchronize()
            start = time.perf_counter()
            optimizer.zero_grad()
            out = model(dummy_input, labels=dummy_labels, use_gradient_checkpointing=config.get("gradient_checkpointing", False))
            loss = out["loss"]
            loss.backward()
            optimizer.step()
            if device == "cuda":
                torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
        monitor.stop()

        total_tokens = config["batch_size"] * config.get("max_position_embeddings", 1024)
        avg_time = sum(times) / len(times) if times else 0.0
        tokens_per_sec = (total_tokens / avg_time) if avg_time > 0 else 0.0

        metrics = {
            "vendor": "nvidia",
            "steps": steps,
            "times_seconds": times,
            "avg_step_time_seconds": round(avg_time, 4),
            "tokens_per_second": round(tokens_per_sec, 2),
            "total_tokens_per_step": total_tokens,
            "gpu_utilization_avg_percent": self._avg_from_samples(monitor, "gpu_utilization_percent"),
        }

        return BenchmarkResult(
            name=f"nvidia_training_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def memory_bandwidth_benchmark(self, size_mb: int = 256, device: str = "cuda") -> BenchmarkResult:
        import torch

        size_bytes = size_mb * 1024 * 1024
        elements = size_bytes // 4
        x = torch.randn(elements, dtype=torch.float32, device=device)
        y = torch.randn(elements, dtype=torch.float32, device=device)

        if device == "cuda":
            torch.cuda.synchronize()
        start = time.perf_counter()
        for _ in range(10):
            y.copy_(x)
        if device == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - start

        bandwidth_gb_per_s = (size_bytes * 10) / (elapsed * 1e9) if elapsed > 0 else 0.0
        metrics = {
            "vendor": "nvidia",
            "device": device,
            "size_mb": size_mb,
            "elapsed_seconds": round(elapsed, 4),
            "bandwidth_gb_per_s": round(bandwidth_gb_per_s, 2),
            "theoretical_bandwidth_gb_per_s": self.profile.bandwidth_gb_per_s,
            "bandwidth_efficiency": round(bandwidth_gb_per_s / self.profile.bandwidth_gb_per_s, 4) if self.profile.bandwidth_gb_per_s else 0.0,
        }

        return BenchmarkResult(
            name=f"nvidia_memory_bandwidth_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def power_usage_benchmark(self, device: str = "cuda") -> BenchmarkResult:
        power_readings: List[float] = []
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            for _ in range(20):
                power_mw = pynvml.nvmlDeviceGetPowerUsage(handle)
                power_readings.append(power_mw / 1000.0)
                time.sleep(0.1)
        except Exception:
            pass

        power_readings = power_readings or [0.0]
        metrics = {
            "vendor": "nvidia",
            "device": device,
            "power_readings_watts": power_readings,
            "avg_power_watts": round(statistics.mean(power_readings), 2),
            "min_power_watts": round(min(power_readings), 2),
            "max_power_watts": round(max(power_readings), 2),
            "profile_power_watts": self.profile.power_watts,
        }

        return BenchmarkResult(
            name=f"nvidia_power_usage_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def cost_per_token(self, tokens_per_second: float) -> float:
        cost_per_hour = self.profile.cost_per_hour
        tokens_per_hour = tokens_per_second * 3600.0
        return cost_per_hour / tokens_per_hour if tokens_per_hour > 0 else 0.0

    def _avg_from_samples(self, monitor: SystemMonitor, key: str) -> float:
        values = [s[key] for s in monitor.samples if s.get(key) is not None]
        if not values:
            return 0.0
        return round(statistics.mean(values), 2)


class AmdBenchmark:
    def __init__(self, profile: HardwareProfile) -> None:
        self.profile = profile

    def inference_benchmark(self, model, tokenizer, prompts: List[str], max_new_tokens: int = 32, device: str = "cuda") -> BenchmarkResult:
        metrics = {
            "vendor": "amd",
            "status": "stub",
            "message": "AMD ROCm inference benchmark not implemented",
        }
        return BenchmarkResult(
            name=f"amd_inference_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def training_benchmark(self, model, config: Dict[str, Any], steps: int = 5, device: str = "cuda") -> BenchmarkResult:
        metrics = {
            "vendor": "amd",
            "status": "stub",
            "message": "AMD ROCm training benchmark not implemented",
        }
        return BenchmarkResult(
            name=f"amd_training_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


class IntelCpuBenchmark:
    def __init__(self, profile: HardwareProfile) -> None:
        self.profile = profile

    def inference_benchmark(self, model, tokenizer, prompts: List[str], max_new_tokens: int = 32, device: str = "cpu") -> BenchmarkResult:
        if model is None:
            metrics = {
                "vendor": "intel",
                "status": "stub",
                "message": "No model provided for benchmarking",
                "num_prompts": len(prompts),
                "max_new_tokens": max_new_tokens,
                "avg_latency_seconds": 0.0,
                "avg_tokens_per_second": 0.0,
                "p50_latency_seconds": 0.0,
                "p95_latency_seconds": 0.0,
                "p99_latency_seconds": 0.0,
            }
            return BenchmarkResult(
                name=f"intel_cpu_inference_{self.profile.name}",
                metrics=metrics,
                profile=self.profile,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        from models.llm.inference.engine import InferenceEngine, SamplingParams

        engine = InferenceEngine(model, tokenizer, device=device)
        params = SamplingParams(max_new_tokens=max_new_tokens, temperature=1.0)
        latencies = []
        tokens_per_sec = []

        for prompt in prompts:
            start = time.perf_counter()
            output = engine.generate(prompt, params)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
            tps = output.num_tokens / elapsed if elapsed > 0 else 0.0
            tokens_per_sec.append(tps)

        sorted_latencies = sorted(latencies)
        n = len(latencies)
        metrics = {
            "vendor": "intel",
            "num_prompts": len(prompts),
            "max_new_tokens": max_new_tokens,
            "avg_latency_seconds": round(sum(latencies) / len(latencies), 4) if latencies else 0.0,
            "avg_tokens_per_second": round(sum(tokens_per_sec) / len(tokens_per_sec), 4) if tokens_per_sec else 0.0,
            "p50_latency_seconds": round(sorted_latencies[n // 2], 4) if n else 0.0,
            "p95_latency_seconds": round(sorted_latencies[int(n * 0.95)], 4) if n else 0.0,
            "p99_latency_seconds": round(sorted_latencies[int(n * 0.99)], 4) if n else 0.0,
        }

        return BenchmarkResult(
            name=f"intel_cpu_inference_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def training_benchmark(self, model, config: Dict[str, Any], steps: int = 5, device: str = "cpu") -> BenchmarkResult:
        if model is None:
            total_tokens = config["batch_size"] * config.get("max_position_embeddings", 1024)
            metrics = {
                "vendor": "intel",
                "status": "stub",
                "message": "No model provided for benchmarking",
                "steps": steps,
                "avg_step_time_seconds": 0.0,
                "tokens_per_second": 0.0,
                "total_tokens_per_step": total_tokens,
            }
            return BenchmarkResult(
                name=f"intel_cpu_training_{self.profile.name}",
                metrics=metrics,
                profile=self.profile,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        import torch

        model.train()
        dummy_input = torch.randint(
            0,
            config["vocab_size"],
            (config["batch_size"], config.get("max_position_embeddings", 1024)),
            device=device,
        )
        dummy_labels = dummy_input.clone()
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)

        times = []
        for _ in range(steps):
            start = time.perf_counter()
            optimizer.zero_grad()
            out = model(dummy_input, labels=dummy_labels, use_gradient_checkpointing=config.get("gradient_checkpointing", False))
            loss = out["loss"]
            loss.backward()
            optimizer.step()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        total_tokens = config["batch_size"] * config.get("max_position_embeddings", 1024)
        avg_time = sum(times) / len(times) if times else 0.0
        tokens_per_sec = (total_tokens / avg_time) if avg_time > 0 else 0.0

        metrics = {
            "vendor": "intel",
            "steps": steps,
            "avg_step_time_seconds": round(avg_time, 4),
            "tokens_per_second": round(tokens_per_sec, 2),
            "total_tokens_per_step": total_tokens,
        }

        return BenchmarkResult(
            name=f"intel_cpu_training_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


class AppleSiliconBenchmark:
    def __init__(self, profile: HardwareProfile) -> None:
        self.profile = profile

    def inference_benchmark(self, model, tokenizer, prompts: List[str], max_new_tokens: int = 32, device: str = "mps") -> BenchmarkResult:
        metrics = {
            "vendor": "apple",
            "status": "stub",
            "message": "Apple Silicon inference benchmark not implemented",
        }
        return BenchmarkResult(
            name=f"apple_inference_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def training_benchmark(self, model, config: Dict[str, Any], steps: int = 5, device: str = "mps") -> BenchmarkResult:
        metrics = {
            "vendor": "apple",
            "status": "stub",
            "message": "Apple Silicon training benchmark not implemented",
        }
        return BenchmarkResult(
            name=f"apple_training_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


class MemoryBandwidthBenchmark:
    def __init__(self, profile: HardwareProfile) -> None:
        self.profile = profile

    def run(self, size_mb: int = 256, device: str = "cpu") -> BenchmarkResult:
        import torch

        size_bytes = size_mb * 1024 * 1024
        elements = size_bytes // 4
        x = torch.randn(elements, dtype=torch.float32, device=device)
        y = torch.randn(elements, dtype=torch.float32, device=device)

        start = time.perf_counter()
        for _ in range(10):
            y.copy_(x)
        elapsed = time.perf_counter() - start

        bandwidth_gb_per_s = (size_bytes * 10) / (elapsed * 1e9) if elapsed > 0 else 0.0
        metrics = {
            "device": device,
            "size_mb": size_mb,
            "elapsed_seconds": round(elapsed, 4),
            "bandwidth_gb_per_s": round(bandwidth_gb_per_s, 2),
            "theoretical_bandwidth_gb_per_s": self.profile.bandwidth_gb_per_s,
            "bandwidth_efficiency": round(bandwidth_gb_per_s / self.profile.bandwidth_gb_per_s, 4) if self.profile.bandwidth_gb_per_s else 0.0,
        }

        return BenchmarkResult(
            name=f"memory_bandwidth_{self.profile.name}",
            metrics=metrics,
            profile=self.profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


class CostPerTokenCalculator:
    def __init__(self, profile: HardwareProfile) -> None:
        self.profile = profile

    def calculate(self, tokens_per_second: float) -> Dict[str, float]:
        tokens_per_hour = tokens_per_second * 3600.0
        cost_per_hour = self.profile.cost_per_hour
        cost_per_token = cost_per_hour / tokens_per_hour if tokens_per_hour > 0 else 0.0
        cost_per_1k_tokens = cost_per_token * 1000.0
        cost_per_1m_tokens = cost_per_token * 1_000_000.0
        return {
            "tokens_per_second": tokens_per_second,
            "tokens_per_hour": round(tokens_per_hour, 2),
            "cost_per_hour": cost_per_hour,
            "cost_per_token": round(cost_per_token, 8),
            "cost_per_1k_tokens": round(cost_per_1k_tokens, 6),
            "cost_per_1m_tokens": round(cost_per_1m_tokens, 4),
        }
