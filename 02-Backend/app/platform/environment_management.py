"""Environment management for multi-stage deployments."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class EnvironmentType(Enum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DR = "disaster_recovery"


@dataclass
class Environment:
    env_id: str
    name: str
    env_type: EnvironmentType
    cluster: str
    namespace: str
    replicas: int = 1
    resources: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EnvironmentManager:
    _environments: Dict[str, Environment] = {}

    @classmethod
    def create_environment(cls, environment: Environment) -> Environment:
        cls._environments[environment.env_id] = environment
        return environment

    @classmethod
    def get_environment(cls, env_id: str) -> Optional[Environment]:
        return cls._environments.get(env_id)

    @classmethod
    def list_environments(cls) -> List[Environment]:
        return list(cls._environments.values())
