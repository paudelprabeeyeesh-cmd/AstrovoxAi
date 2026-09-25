"""Self-service deployment manager."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class DeploymentStrategy(Enum):
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"


@dataclass
class DeploymentRequest:
    request_id: str
    service_name: str
    image_tag: str
    strategy: DeploymentStrategy
    replicas: int = 1
    env_vars: Dict[str, str] = field(default_factory=dict)
    requested_by: str = "system"
    status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SelfServiceDeployment:
    _requests: Dict[str, DeploymentRequest] = {}

    @classmethod
    def submit_request(cls, request: DeploymentRequest) -> DeploymentRequest:
        cls._requests[request.request_id] = request
        return request

    @classmethod
    def approve_request(cls, request_id: str) -> bool:
        request = cls._requests.get(request_id)
        if request:
            request.status = "approved"
            return True
        return False

    @classmethod
    def get_request(cls, request_id: str) -> Optional[DeploymentRequest]:
        return cls._requests.get(request_id)
