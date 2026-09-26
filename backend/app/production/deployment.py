from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class DeploymentConfig:
    service: str
    image: str
    replicas: int
    env: Dict[str, str] = None

    def __post_init__(self):
        if self.env is None:
            self.env = {}


class DeploymentManager:
    def __init__(self, configs: List[DeploymentConfig]):
        self.configs = {c.service: c for c in configs}

    def deploy(self, service: str) -> None:
        config = self.configs.get(service)
        if not config:
            raise ValueError(f"Unknown service: {service}")
        print(f"Deploying {service} with image {config.image} replicas {config.replicas}")

    def rollback(self, service: str) -> None:
        print(f"Rolling back {service}")
