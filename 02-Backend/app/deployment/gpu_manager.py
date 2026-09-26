from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..deployment.base_adapter import BaseCloudAdapter


class GPUInstanceType(Enum):
    AWS_P3 = "p3.2xlarge"
    AWS_P4 = "p4d.24xlarge"
    AWS_G5 = "g5.xlarge"
    AZURE_NC = "Standard_NC6s_v3"
    AZURE_ND = "Standard_ND40rs_v2"
    GCP_A2 = "a2-highgpu-1g"
    GCP_A100 = "a2-ultragpu-1g"


@dataclass
class GPUInstanceConfig:
    instance_type: GPUInstanceType
    count: int = 1
    image_id: Optional[str] = None
    key_name: Optional[str] = None
    startup_script: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class GPUInstanceManager:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.instances: Dict[str, List[str]] = {}

    def provision(self, config: GPUInstanceConfig) -> Dict[str, Any]:
        result = self.adapter.provision_gpu_instance(
            config.instance_type.value,
            config.count,
        )
        self.instances[config.instance_type.value] = result.get("instance_ids", [])
        return result

    def terminate(self, instance_type: GPUInstanceType) -> Dict[str, Any]:
        if instance_type.value not in self.instances:
            return {"status": "no_instances"}
        instance_ids = self.instances[instance_type.value]
        return {
            "status": "terminated",
            "instance_type": instance_type.value,
            "instance_ids": instance_ids,
        }

    def get_instance_status(self, instance_type: GPUInstanceType) -> Dict[str, Any]:
        instance_ids = self.instances.get(instance_type.value, [])
        return {
            "instance_type": instance_type.value,
            "count": len(instance_ids),
            "instance_ids": instance_ids,
        }
