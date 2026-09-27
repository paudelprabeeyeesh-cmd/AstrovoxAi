"""Docker configuration management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DockerConfig:
    config_id: str
    image: str
    ports: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: List[str] = field(default_factory=list)


@dataclass
class DockerCompose:
    compose_id: str
    services: Dict[str, DockerConfig]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DockerManager:
    def __init__(self) -> None:
        self._configs: Dict[str, DockerConfig] = {}
        self._composes: Dict[str, DockerCompose] = {}

    def register_config(self, config: DockerConfig) -> None:
        self._configs[config.config_id] = config

    def create_compose(self, compose: DockerCompose) -> DockerCompose:
        self._composes[compose.compose_id] = compose
        return compose


docker_manager = DockerManager()
