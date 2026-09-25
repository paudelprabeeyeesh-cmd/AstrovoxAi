from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..deployment.base_adapter import BaseCloudAdapter, DeploymentConfig


class EdgeRuntime(Enum):
    LAMBDA = "lambda"
    FUNCTIONS = "functions"
    CLOUD_FUNCTIONS = "cloud_functions"


@dataclass
class EdgeFunctionConfig:
    name: str
    runtime: EdgeRuntime
    memory_mb: int = 128
    timeout_seconds: int = 30
    environment: Optional[Dict[str, str]] = None
    code_uri: Optional[str] = None
    handler: Optional[str] = None


class EdgeInferenceManager:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.functions: Dict[str, EdgeFunctionConfig] = {}

    def deploy_function(self, config: EdgeFunctionConfig) -> Dict[str, Any]:
        self.functions[config.name] = config
        return self.adapter.deploy_edge_function(
            config.name,
            config.runtime.value,
            config.code_uri or "",
        )

    def update_function(self, name: str, code_uri: str) -> Dict[str, Any]:
        if name not in self.functions:
            raise ValueError(f"Function {name} not found")
        self.functions[name].code_uri = code_uri
        return self.adapter.deploy_edge_function(name, self.functions[name].runtime.value, code_uri)

    def get_function(self, name: str) -> Optional[EdgeFunctionConfig]:
        return self.functions.get(name)

    def list_functions(self) -> List[str]:
        return list(self.functions.keys())
