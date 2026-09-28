import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.benchmarks.hardware import (
    AmdBenchmark,
    AppleSiliconBenchmark,
    BenchmarkResult,
    CostPerTokenCalculator,
    IntelCpuBenchmark,
    MemoryBandwidthBenchmark,
    NvidiaBenchmark,
)
from models.llm.benchmarks.profiles import (
    APPLE_SILICON_PROFILES,
    CPU_PROFILES,
    GPU_PROFILES,
    AppleSiliconProfile,
    CpuProfile,
    GpuProfile,
    HardwareProfile,
    detect_hardware,
    get_apple_silicon_profile,
    get_cpu_profile,
    get_gpu_profile,
    list_apple_silicon_profiles,
    list_cpu_profiles,
    list_gpu_profiles,
)


class TestHardwareProfiles:
    def test_gpu_profiles_exist(self):
        assert len(GPU_PROFILES) > 0
        for name, profile in GPU_PROFILES.items():
            assert isinstance(profile, GpuProfile)
            assert profile.vendor
            assert profile.device_type == "gpu"
            assert profile.memory_gb > 0

    def test_cpu_profiles_exist(self):
        assert len(CPU_PROFILES) > 0
        for name, profile in CPU_PROFILES.items():
            assert isinstance(profile, CpuProfile)
            assert profile.vendor
            assert profile.device_type == "cpu"

    def test_apple_silicon_profiles_exist(self):
        assert len(APPLE_SILICON_PROFILES) > 0
        for name, profile in APPLE_SILICON_PROFILES.items():
            assert isinstance(profile, AppleSiliconProfile)
            assert profile.vendor == "apple"
            assert profile.device_type == "apple_silicon"

    def test_get_gpu_profile(self):
        profile = get_gpu_profile("a100_80g")
        assert profile.name == "a100_80g"
        assert profile.bandwidth_gb_per_s > 0

    def test_get_gpu_profile_invalid(self):
        with pytest.raises(KeyError):
            get_gpu_profile("nonexistent_gpu")

    def test_get_cpu_profile(self):
        profile = get_cpu_profile("intel_xeon_platinum_8480")
        assert profile.cores == 56

    def test_get_apple_silicon_profile(self):
        profile = get_apple_silicon_profile("m1_max")
        assert profile.unified_memory_gb == 32.0

    def test_list_gpu_profiles(self):
        names = list_gpu_profiles()
        assert "a100_80g" in names
        assert "h100_80g" in names

    def test_list_cpu_profiles(self):
        names = list_cpu_profiles()
        assert "intel_xeon_platinum_8480" in names

    def test_list_apple_silicon_profiles(self):
        names = list_apple_silicon_profiles()
        assert "m1" in names
        assert "m3_max" in names


class TestHardwareDetection:
    def test_detect_hardware_returns_profile_or_none(self):
        result = detect_hardware()
        assert result is None or isinstance(result, HardwareProfile)

    def test_detected_profile_attributes(self):
        profile = detect_hardware()
        if profile is not None:
            assert hasattr(profile, "name")
            assert hasattr(profile, "vendor")
            assert hasattr(profile, "device_type")


class TestNvidiaBenchmark:
    def test_inference_benchmark_returns_result(self):
        profile = get_gpu_profile("a100_80g")
        benchmark = NvidiaBenchmark(profile)
        result = benchmark.inference_benchmark(None, None, ["test prompt"], max_new_tokens=4, device="cpu")
        assert isinstance(result, BenchmarkResult)
        assert result.metrics["vendor"] == "nvidia"
        assert "avg_latency_seconds" in result.metrics

    def test_training_benchmark_returns_result(self):
        profile = get_gpu_profile("a100_80g")
        benchmark = NvidiaBenchmark(profile)
        result = benchmark.training_benchmark(None, {"vocab_size": 1000, "hidden_size": 32, "num_hidden_layers": 2, "num_attention_heads": 2, "intermediate_size": 64, "max_position_embeddings": 64, "batch_size": 2, "gradient_checkpointing": False}, steps=1, device="cpu")
        assert isinstance(result, BenchmarkResult)
        assert result.metrics["vendor"] == "nvidia"
        assert "avg_step_time_seconds" in result.metrics

    def test_memory_bandwidth_benchmark_returns_result(self):
        profile = get_gpu_profile("a100_80g")
        benchmark = NvidiaBenchmark(profile)
        result = benchmark.memory_bandwidth_benchmark(size_mb=64, device="cpu")
        assert isinstance(result, BenchmarkResult)
        assert result.metrics["bandwidth_gb_per_s"] >= 0

    def test_power_usage_benchmark_returns_result(self):
        profile = get_gpu_profile("a100_80g")
        benchmark = NvidiaBenchmark(profile)
        result = benchmark.power_usage_benchmark(device="cpu")
        assert isinstance(result, BenchmarkResult)
        assert "avg_power_watts" in result.metrics

    def test_cost_per_token(self):
        profile = get_gpu_profile("a100_80g")
        benchmark = NvidiaBenchmark(profile)
        cost = benchmark.cost_per_token(tokens_per_second=1000.0)
        assert cost >= 0
        assert isinstance(cost, float)


class TestAmdBenchmark:
    def test_inference_benchmark_stub(self):
        profile = get_gpu_profile("radeon_pro_v620_32g")
        benchmark = AmdBenchmark(profile)
        result = benchmark.inference_benchmark(None, None, ["test"])
        assert result.metrics["status"] == "stub"

    def test_training_benchmark_stub(self):
        profile = get_gpu_profile("radeon_pro_v620_32g")
        benchmark = AmdBenchmark(profile)
        result = benchmark.training_benchmark(None, {"vocab_size": 1000, "hidden_size": 32, "num_hidden_layers": 2, "num_attention_heads": 2, "intermediate_size": 64, "max_position_embeddings": 64, "batch_size": 2}, steps=1, device="cpu")
        assert result.metrics["status"] == "stub"


class TestIntelCpuBenchmark:
    def test_inference_benchmark_returns_result(self):
        profile = get_cpu_profile("intel_xeon_platinum_8480")
        benchmark = IntelCpuBenchmark(profile)
        result = benchmark.inference_benchmark(None, None, ["test prompt"], max_new_tokens=4, device="cpu")
        assert isinstance(result, BenchmarkResult)
        assert result.metrics["vendor"] == "intel"
        assert "avg_latency_seconds" in result.metrics

    def test_training_benchmark_returns_result(self):
        profile = get_cpu_profile("intel_xeon_platinum_8480")
        benchmark = IntelCpuBenchmark(profile)
        result = benchmark.training_benchmark(None, {"vocab_size": 1000, "hidden_size": 32, "num_hidden_layers": 2, "num_attention_heads": 2, "intermediate_size": 64, "max_position_embeddings": 64, "batch_size": 2, "gradient_checkpointing": False}, steps=1, device="cpu")
        assert isinstance(result, BenchmarkResult)
        assert result.metrics["vendor"] == "intel"
        assert "avg_step_time_seconds" in result.metrics


class TestAppleSiliconBenchmark:
    def test_inference_benchmark_stub(self):
        profile = get_apple_silicon_profile("m1_max")
        benchmark = AppleSiliconBenchmark(profile)
        result = benchmark.inference_benchmark(None, None, ["test"])
        assert result.metrics["status"] == "stub"

    def test_training_benchmark_stub(self):
        profile = get_apple_silicon_profile("m1_max")
        benchmark = AppleSiliconBenchmark(profile)
        result = benchmark.training_benchmark(None, {"vocab_size": 1000, "hidden_size": 32, "num_hidden_layers": 2, "num_attention_heads": 2, "intermediate_size": 64, "max_position_embeddings": 64, "batch_size": 2}, steps=1, device="cpu")
        assert result.metrics["status"] == "stub"


class TestMemoryBandwidthBenchmark:
    def test_run_returns_result(self):
        profile = get_cpu_profile("intel_core_i9_13900k")
        benchmark = MemoryBandwidthBenchmark(profile)
        result = benchmark.run(size_mb=64, device="cpu")
        assert isinstance(result, BenchmarkResult)
        assert result.metrics["bandwidth_gb_per_s"] >= 0
        assert "bandwidth_efficiency" in result.metrics


class TestCostPerTokenCalculator:
    def test_calculate_returns_metrics(self):
        profile = get_gpu_profile("a100_80g")
        calculator = CostPerTokenCalculator(profile)
        metrics = calculator.calculate(tokens_per_second=1000.0)
        assert "cost_per_token" in metrics
        assert "cost_per_1k_tokens" in metrics
        assert "cost_per_1m_tokens" in metrics
        assert metrics["cost_per_token"] >= 0

    def test_zero_tps_gives_zero_cost_per_token(self):
        profile = get_gpu_profile("a100_80g")
        calculator = CostPerTokenCalculator(profile)
        metrics = calculator.calculate(tokens_per_second=0.0)
        assert metrics["cost_per_token"] == 0.0
