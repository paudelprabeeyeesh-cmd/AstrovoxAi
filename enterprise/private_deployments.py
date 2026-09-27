"""
Private deployments for AstrovoxAI.
Manages dedicated, on-premise, and private cloud deployments for enterprise customers.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeploymentEnvironment(str, Enum):
    ON_PREMISE = "on_premise"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    PRIVATE_CLOUD = "private_cloud"


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    DEPLOYING = "deploying"
    RUNNING = "running"
    UPDATING = "updating"
    SCALING = "scaling"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class DeploymentConfig:
    environment: DeploymentEnvironment
    region: str
    instance_type: str
    min_instances: int
    max_instances: int
    storage_gb: int
    custom_domain: Optional[str] = None
    vpc_cidr: Optional[str] = None
    private_endpoints: bool = False
    encryption_at_rest: bool = True
    network_whitelist: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment": self.environment.value,
            "region": self.region,
            "instance_type": self.instance_type,
            "min_instances": self.min_instances,
            "max_instances": self.max_instances,
            "storage_gb": self.storage_gb,
            "custom_domain": self.custom_domain,
            "vpc_cidr": self.vpc_cidr,
            "private_endpoints": self.private_endpoints,
            "encryption_at_rest": self.encryption_at_rest,
            "network_whitelist": self.network_whitelist,
        }


@dataclass
class PrivateDeployment:
    deployment_id: str
    developer_id: str
    name: str
    config: DeploymentConfig
    status: DeploymentStatus
    endpoint_url: Optional[str]
    api_key: Optional[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment_id": self.deployment_id,
            "developer_id": self.developer_id,
            "name": self.name,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "endpoint_url": self.endpoint_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
        }


class PrivateDeploymentManager:
    """Manages private deployments for enterprise customers."""

    def __init__(self):
        self._deployments: Dict[str, PrivateDeployment] = {}

    def create_deployment(
        self,
        developer_id: str,
        name: str,
        config: DeploymentConfig,
    ) -> PrivateDeployment:
        deployment = PrivateDeployment(
            deployment_id=str(uuid.uuid4()),
            developer_id=developer_id,
            name=name,
            config=config,
            status=DeploymentStatus.PENDING,
            endpoint_url=None,
            api_key=None,
        )
        self._deployments[deployment.deployment_id] = deployment
        logger.info("Created private deployment %s for developer %s", deployment.deployment_id, developer_id)
        return deployment

    def get_deployment(self, deployment_id: str) -> Optional[PrivateDeployment]:
        return self._deployments.get(deployment_id)

    def list_deployments(self, developer_id: str) -> List[PrivateDeployment]:
        return [d for d in self._deployments.values() if d.developer_id == developer_id]

    def update_deployment(self, deployment_id: str, config: DeploymentConfig) -> PrivateDeployment:
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError("Deployment not found")
        deployment.config = config
        deployment.updated_at = datetime.utcnow()
        logger.info("Updated deployment %s", deployment_id)
        return deployment

    def scale_deployment(self, deployment_id: str, min_instances: int, max_instances: int) -> None:
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError("Deployment not found")
        deployment.config.min_instances = min_instances
        deployment.config.max_instances = max_instances
        deployment.status = DeploymentStatus.SCALING
        deployment.updated_at = datetime.utcnow()
        logger.info("Scaling deployment %s to %d-%d instances", deployment_id, min_instances, max_instances)

    def delete_deployment(self, deployment_id: str) -> None:
        if deployment_id in self._deployments:
            del self._deployments[deployment_id]
            logger.info("Deleted deployment %s", deployment_id)
