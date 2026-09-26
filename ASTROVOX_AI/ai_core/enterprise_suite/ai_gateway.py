from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class PrivateDeployment:
    deployment_id: str
    model_id: str
    vpc_id: str
    region: str
    status: str = "provisioning"


class EnterpriseModelManager:
    def __init__(self):
        self.deployments: Dict[str, PrivateDeployment] = {}

    def provision(self, model_id: str, vpc_id: str, region: str) -> PrivateDeployment:
        deployment = PrivateDeployment(
            deployment_id=str(len(self.deployments) + 1),
            model_id=model_id,
            vpc_id=vpc_id,
            region=region,
        )
        self.deployments[deployment.deployment_id] = deployment
        return deployment
