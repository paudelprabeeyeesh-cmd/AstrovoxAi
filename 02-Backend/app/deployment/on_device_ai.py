from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class DeviceType(Enum):
    IOS = "ios"
    ANDROID = "android"
    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"


class AcceleratorType(Enum):
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"
    NPU = "npu"
    CUSTOM = "custom"


@dataclass
class OnDeviceModelConfig:
    device_type: DeviceType
    model_name: str
    model_path: str
    accelerator: AcceleratorType = AcceleratorType.CPU
    memory_limit_mb: int = 512
    quantized: bool = False


class OnDeviceAIManager:
    def __init__(self):
        self.models: Dict[str, OnDeviceModelConfig] = {}

    def register_model(self, config: OnDeviceModelConfig) -> Dict[str, Any]:
        self.models[config.model_name] = config
        return {
            "status": "registered",
            "model_name": config.model_name,
            "device_type": config.device_type.value,
            "accelerator": config.accelerator.value,
        }

    def get_model(self, model_name: str) -> Optional[OnDeviceModelConfig]:
        return self.models.get(model_name)

    def list_models(self) -> List[str]:
        return list(self.models.keys())

    def generate_stub(self, model_name: str) -> Dict[str, Any]:
        model = self.get_model(model_name)
        if not model:
            raise ValueError(f"Model {model_name} not found")
        return {
            "model_name": model_name,
            "stub": f"stub_{model_name.lower().replace('-', '_')}",
            "device_type": model.device_type.value,
            "accelerator": model.accelerator.value,
        }
