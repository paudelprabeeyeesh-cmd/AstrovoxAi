from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..deployment.base_adapter import BaseCloudAdapter


class AcceleratorVendor(Enum):
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    CUSTOM = "custom"


class AcceleratorType(Enum):
    GPU = "gpu"
    TPU = "tpu"
    IPU = "ipu"
    VPU = "vpu"


@dataclass
class AcceleratorConfig:
    vendor: AcceleratorVendor
    accelerator_type: AcceleratorType
    model: str
    memory_gb: int
    count: int = 1
    driver_version: Optional[str] = None


class CustomAcceleratorManager:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.accelerators: Dict[str, AcceleratorConfig] = {}

    def register_accelerator(self, config: AcceleratorConfig) -> Dict[str, Any]:
        key = f"{config.vendor.value}_{config.model}"
        self.accelerators[key] = config
        return {
            "status": "registered",
            "vendor": config.vendor.value,
            "model": config.model,
            "type": config.accelerator_type.value,
            "memory_gb": config.memory_gb,
        }

    def provision_accelerator(self, accelerator_key: str) -> Dict[str, Any]:
        if accelerator_key not in self.accelerators:
            raise ValueError(f"Accelerator {accelerator_key} not found")
        config = self.accelerators[accelerator_key]
        return self.adapter.provision_gpu_instance(
            config.model,
            config.count,
        )

    def get_accelerator(self, accelerator_key: str) -> Optional[AcceleratorConfig]:
        return self.accelerators.get(accelerator_key)

    def list_accelerators(self) -> List[str]:
        return list(self.accelerators.keys())
