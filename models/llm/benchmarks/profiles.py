from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional

from models.llm.benchmarks.hardware import HardwareProfile


@dataclass
class GpuProfile(HardwareProfile):
    cuda_cores: int = 0
    tensor_cores: int = 0
    memory_bus_width: int = 0
    supported_precisions: List[str] = None

    def __post_init__(self) -> None:
        if self.supported_precisions is None:
            self.supported_precisions = ["fp32", "fp16", "bf16"]


@dataclass
class CpuProfile(HardwareProfile):
    cores: int = 0
    threads: int = 0
    base_clock_ghz: float = 0.0
    boost_clock_ghz: float = 0.0
    cache_mb: float = 0.0
    simd_support: List[str] = None

    def __post_init__(self) -> None:
        if self.simd_support is None:
            self.simd_support = ["avx2"]


@dataclass
class AppleSiliconProfile(HardwareProfile):
    chip_variant: str = ""
    cpu_cores: int = 0
    gpu_cores: int = 0
    neural_engine_cores: int = 0
    unified_memory_gb: float = 0.0
    metal_support: bool = True


GPU_PROFILES: Dict[str, GpuProfile] = {
    "a100_80g": GpuProfile(
        vendor="nvidia",
        name="a100_80g",
        device_type="gpu",
        memory_gb=80.0,
        compute_capability="sm_80",
        bandwidth_gb_per_s=2039.0,
        peak_tflops=312.0,
        power_watts=400.0,
        cost_per_hour=4.0,
        cuda_cores=6912,
        tensor_cores=432,
        memory_bus_width=5120,
        supported_precisions=["fp32", "fp16", "bf16", "tf32"],
        metadata={"architecture": "ampere"},
    ),
    "a100_40g": GpuProfile(
        vendor="nvidia",
        name="a100_40g",
        device_type="gpu",
        memory_gb=40.0,
        compute_capability="sm_80",
        bandwidth_gb_per_s=1555.0,
        peak_tflops=312.0,
        power_watts=400.0,
        cost_per_hour=3.0,
        cuda_cores=6912,
        tensor_cores=432,
        memory_bus_width=5120,
        supported_precisions=["fp32", "fp16", "bf16", "tf32"],
        metadata={"architecture": "ampere"},
    ),
    "h100_80g": GpuProfile(
        vendor="nvidia",
        name="h100_80g",
        device_type="gpu",
        memory_gb=80.0,
        compute_capability="sm_90",
        bandwidth_gb_per_s=3350.0,
        peak_tflops=3958.0,
        power_watts=700.0,
        cost_per_hour=10.0,
        cuda_cores=16896,
        tensor_cores=528,
        memory_bus_width=6144,
        supported_precisions=["fp32", "fp16", "bf16", "fp8", "tf32"],
        metadata={"architecture": "hopper"},
    ),
    "l40_48g": GpuProfile(
        vendor="nvidia",
        name="l40_48g",
        device_type="gpu",
        memory_gb=48.0,
        compute_capability="sm_89",
        bandwidth_gb_per_s=864.0,
        peak_tflops=366.0,
        power_watts=350.0,
        cost_per_hour=1.5,
        cuda_cores=16128,
        tensor_cores=512,
        memory_bus_width=384,
        supported_precisions=["fp32", "fp16", "bf16", "tf32"],
        metadata={"architecture": "ada_lovelace"},
    ),
    "rtx4090_24g": GpuProfile(
        vendor="nvidia",
        name="rtx4090_24g",
        device_type="gpu",
        memory_gb=24.0,
        compute_capability="sm_89",
        bandwidth_gb_per_s=1008.0,
        peak_tflops=82.6,
        power_watts=450.0,
        cost_per_hour=0.5,
        cuda_cores=16384,
        tensor_cores=512,
        memory_bus_width=384,
        supported_precisions=["fp32", "fp16", "bf16", "tf32"],
        metadata={"architecture": "ada_lovelace"},
    ),
    "rtx3090_24g": GpuProfile(
        vendor="nvidia",
        name="rtx3090_24g",
        device_type="gpu",
        memory_gb=24.0,
        compute_capability="sm_86",
        bandwidth_gb_per_s=936.0,
        peak_tflops=35.6,
        power_watts=350.0,
        cost_per_hour=0.3,
        cuda_cores=10496,
        tensor_cores=328,
        memory_bus_width=384,
        supported_precisions=["fp32", "fp16", "bf16", "tf32"],
        metadata={"architecture": "ampere"},
    ),
    "rtx3080_10g": GpuProfile(
        vendor="nvidia",
        name="rtx3080_10g",
        device_type="gpu",
        memory_gb=10.0,
        compute_capability="sm_86",
        bandwidth_gb_per_s=760.0,
        peak_tflops=29.8,
        power_watts=320.0,
        cost_per_hour=0.2,
        cuda_cores=8704,
        tensor_cores=272,
        memory_bus_width=320,
        supported_precisions=["fp32", "fp16", "bf16", "tf32"],
        metadata={"architecture": "ampere"},
    ),
    "v100_32g": GpuProfile(
        vendor="nvidia",
        name="v100_32g",
        device_type="gpu",
        memory_gb=32.0,
        compute_capability="sm_70",
        bandwidth_gb_per_s=900.0,
        peak_tflops=125.0,
        power_watts=300.0,
        cost_per_hour=2.0,
        cuda_cores=5120,
        tensor_cores=640,
        memory_bus_width=4096,
        supported_precisions=["fp32", "fp16", "bf16", "tf32"],
        metadata={"architecture": "volta"},
    ),
    "t4_16g": GpuProfile(
        vendor="nvidia",
        name="t4_16g",
        device_type="gpu",
        memory_gb=16.0,
        compute_capability="sm_75",
        bandwidth_gb_per_s=320.0,
        peak_tflops=65.0,
        power_watts=70.0,
        cost_per_hour=0.5,
        cuda_cores=2560,
        tensor_cores=320,
        memory_bus_width=256,
        supported_precisions=["fp32", "fp16", "bf16", "int8", "int4"],
        metadata={"architecture": "turing"},
    ),
    "radeon_pro_v620_32g": GpuProfile(
        vendor="amd",
        name="radeon_pro_v620_32g",
        device_type="gpu",
        memory_gb=32.0,
        compute_capability="gfx1030",
        bandwidth_gb_per_s=960.0,
        peak_tflops=20.0,
        power_watts=250.0,
        cost_per_hour=1.0,
        cuda_cores=0,
        tensor_cores=0,
        memory_bus_width=256,
        supported_precisions=["fp32", "fp16", "bf16"],
        metadata={"architecture": "rdna2"},
    ),
}

CPU_PROFILES: Dict[str, CpuProfile] = {
    "intel_xeon_platinum_8480": CpuProfile(
        vendor="intel",
        name="intel_xeon_platinum_8480",
        device_type="cpu",
        cores=56,
        threads=112,
        base_clock_ghz=2.0,
        boost_clock_ghz=3.8,
        cache_mb=105.0,
        simd_support=["avx512", "avx2"],
        memory_gb=0.0,
        bandwidth_gb_per_s=0.0,
        peak_tflops=4.0,
        power_watts=350.0,
        cost_per_hour=1.5,
    ),
    "intel_xeon_gold_6330": CpuProfile(
        vendor="intel",
        name="intel_xeon_gold_6330",
        device_type="cpu",
        cores=28,
        threads=56,
        base_clock_ghz=2.0,
        boost_clock_ghz=3.2,
        cache_mb=42.0,
        simd_support=["avx512", "avx2"],
        memory_gb=0.0,
        bandwidth_gb_per_s=0.0,
        peak_tflops=2.0,
        power_watts=205.0,
        cost_per_hour=0.8,
    ),
    "intel_core_i9_13900k": CpuProfile(
        vendor="intel",
        name="intel_core_i9_13900k",
        device_type="cpu",
        cores=24,
        threads=32,
        base_clock_ghz=3.0,
        boost_clock_ghz=5.8,
        cache_mb=36.0,
        simd_support=["avx512", "avx2"],
        memory_gb=0.0,
        bandwidth_gb_per_s=0.0,
        peak_tflops=0.8,
        power_watts=253.0,
        cost_per_hour=0.3,
    ),
    "amd_epyc_9654": CpuProfile(
        vendor="amd",
        name="amd_epyc_9654",
        device_type="cpu",
        cores=96,
        threads=192,
        base_clock_ghz=2.4,
        boost_clock_ghz=3.7,
        cache_mb=384.0,
        simd_support=["avx2", "avx512"],
        memory_gb=0.0,
        bandwidth_gb_per_s=0.0,
        peak_tflops=5.0,
        power_watts=400.0,
        cost_per_hour=1.2,
    ),
    "apple_m2_max": CpuProfile(
        vendor="apple",
        name="apple_m2_max",
        device_type="cpu",
        cores=12,
        threads=12,
        base_clock_ghz=3.5,
        boost_clock_ghz=3.7,
        cache_mb=48.0,
        simd_support=["neon"],
        memory_gb=0.0,
        bandwidth_gb_per_s=0.0,
        peak_tflops=0.5,
        power_watts=30.0,
        cost_per_hour=0.2,
    ),
}

APPLE_SILICON_PROFILES: Dict[str, AppleSiliconProfile] = {
    "m1": AppleSiliconProfile(
        vendor="apple",
        name="m1",
        device_type="apple_silicon",
        memory_gb=16.0,
        bandwidth_gb_per_s=68.25,
        peak_tflops=2.6,
        power_watts=15.0,
        cost_per_hour=0.1,
        chip_variant="m1",
        cpu_cores=8,
        gpu_cores=8,
        neural_engine_cores=16,
        unified_memory_gb=16.0,
    ),
    "m1_pro": AppleSiliconProfile(
        vendor="apple",
        name="m1_pro",
        device_type="apple_silicon",
        memory_gb=16.0,
        bandwidth_gb_per_s=200.0,
        peak_tflops=5.5,
        power_watts=30.0,
        cost_per_hour=0.15,
        chip_variant="m1_pro",
        cpu_cores=10,
        gpu_cores=16,
        neural_engine_cores=16,
        unified_memory_gb=16.0,
    ),
    "m1_max": AppleSiliconProfile(
        vendor="apple",
        name="m1_max",
        device_type="apple_silicon",
        memory_gb=32.0,
        bandwidth_gb_per_s=400.0,
        peak_tflops=10.4,
        power_watts=60.0,
        cost_per_hour=0.25,
        chip_variant="m1_max",
        cpu_cores=10,
        gpu_cores=32,
        neural_engine_cores=16,
        unified_memory_gb=32.0,
    ),
    "m2": AppleSiliconProfile(
        vendor="apple",
        name="m2",
        device_type="apple_silicon",
        memory_gb=16.0,
        bandwidth_gb_per_s=100.0,
        peak_tflops=3.6,
        power_watts=20.0,
        cost_per_hour=0.12,
        chip_variant="m2",
        cpu_cores=8,
        gpu_cores=10,
        neural_engine_cores=16,
        unified_memory_gb=16.0,
    ),
    "m2_pro": AppleSiliconProfile(
        vendor="apple",
        name="m2_pro",
        device_type="apple_silicon",
        memory_gb=16.0,
        bandwidth_gb_per_s=200.0,
        peak_tflops=7.5,
        power_watts=35.0,
        cost_per_hour=0.2,
        chip_variant="m2_pro",
        cpu_cores=12,
        gpu_cores=19,
        neural_engine_cores=16,
        unified_memory_gb=16.0,
    ),
    "m2_max": AppleSiliconProfile(
        vendor="apple",
        name="m2_max",
        device_type="apple_silicon",
        memory_gb=32.0,
        bandwidth_gb_per_s=400.0,
        peak_tflops=13.6,
        power_watts=60.0,
        cost_per_hour=0.3,
        chip_variant="m2_max",
        cpu_cores=12,
        gpu_cores=38,
        neural_engine_cores=16,
        unified_memory_gb=32.0,
    ),
    "m3": AppleSiliconProfile(
        vendor="apple",
        name="m3",
        device_type="apple_silicon",
        memory_gb=18.0,
        bandwidth_gb_per_s=120.0,
        peak_tflops=4.5,
        power_watts=25.0,
        cost_per_hour=0.15,
        chip_variant="m3",
        cpu_cores=8,
        gpu_cores=10,
        neural_engine_cores=16,
        unified_memory_gb=18.0,
    ),
    "m3_pro": AppleSiliconProfile(
        vendor="apple",
        name="m3_pro",
        device_type="apple_silicon",
        memory_gb=18.0,
        bandwidth_gb_per_s=150.0,
        peak_tflops=7.5,
        power_watts=40.0,
        cost_per_hour=0.25,
        chip_variant="m3_pro",
        cpu_cores=12,
        gpu_cores=16,
        neural_engine_cores=16,
        unified_memory_gb=18.0,
    ),
    "m3_max": AppleSiliconProfile(
        vendor="apple",
        name="m3_max",
        device_type="apple_silicon",
        memory_gb=36.0,
        bandwidth_gb_per_s=400.0,
        peak_tflops=14.2,
        power_watts=70.0,
        cost_per_hour=0.35,
        chip_variant="m3_max",
        cpu_cores=16,
        gpu_cores=40,
        neural_engine_cores=16,
        unified_memory_gb=36.0,
    ),
}


def get_gpu_profile(name: str) -> GpuProfile:
    if name not in GPU_PROFILES:
        raise KeyError(f"Unknown GPU profile: {name}. Available: {sorted(GPU_PROFILES.keys())}")
    return GPU_PROFILES[name]


def get_cpu_profile(name: str) -> CpuProfile:
    if name not in CPU_PROFILES:
        raise KeyError(f"Unknown CPU profile: {name}. Available: {sorted(CPU_PROFILES.keys())}")
    return CPU_PROFILES[name]


def get_apple_silicon_profile(name: str) -> AppleSiliconProfile:
    if name not in APPLE_SILICON_PROFILES:
        raise KeyError(f"Unknown Apple Silicon profile: {name}. Available: {sorted(APPLE_SILICON_PROFILES.keys())}")
    return APPLE_SILICON_PROFILES[name]


def list_gpu_profiles() -> List[str]:
    return sorted(GPU_PROFILES.keys())


def list_cpu_profiles() -> List[str]:
    return sorted(CPU_PROFILES.keys())


def list_apple_silicon_profiles() -> List[str]:
    return sorted(APPLE_SILICON_PROFILES.keys())


def detect_hardware() -> Optional[HardwareProfile]:
    system = platform.system().lower()
    if system == "linux" or system == "windows":
        try:
            import torch
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                name = props.name.lower().replace(" ", "_")
                for key, profile in GPU_PROFILES.items():
                    if key in name or name in key:
                        return profile
                return GpuProfile(
                    vendor="nvidia",
                    name=props.name,
                    device_type="gpu",
                    memory_gb=props.total_memory / (1024 ** 3),
                    compute_capability=f"sm_{props.major}{props.minor}",
                    bandwidth_gb_per_s=0.0,
                    peak_tflops=0.0,
                    power_watts=0.0,
                    cost_per_hour=0.0,
                    metadata={"detected": True},
                )
        except Exception:
            pass
    if system == "darwin":
        try:
            cpu_brand = platform.processor() or platform.mac_ver()[0]
            for key, profile in APPLE_SILICON_PROFILES.items():
                if key in cpu_brand.lower() or "m" in cpu_brand.lower():
                    return profile
            for key, profile in CPU_PROFILES.items():
                if "apple" in profile.vendor:
                    return profile
        except Exception:
            pass
    return None
