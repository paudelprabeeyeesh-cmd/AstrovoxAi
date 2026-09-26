"""Container registry configuration."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class RegistryProvider(str, Enum):
    DOCKER_HUB = "docker_hub"
    GITHUB_CR = "github_cr"
    AWS_ECR = "aws_ecr"
    GCP_GCR = "gcp_gcr"
    AZURE_ACR = "azure_acr"


@dataclass
class Image:
    name: str
    tag: str
    digest: str = ""
    size_bytes: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class RegistryConfig:
    provider: RegistryProvider
    url: str
    username: str = ""
    password: str = ""
    namespace: str = ""


class ContainerRegistry:
    """Manage container registry operations."""

    def __init__(self, config: RegistryConfig) -> None:
        self._config = config
        self._images: Dict[str, Image] = {}

    def push_image(self, image: Image) -> str:
        self._images[image.name] = image
        logger.info(f"Pushed image: {image.name}:{image.tag}")
        return f"{self._config.url}/{self._config.namespace}/{image.name}:{image.tag}"

    def pull_image(self, image_name: str, tag: str) -> Optional[Image]:
        key = f"{image_name}:{tag}"
        return self._images.get(key)

    def list_images(self) -> List[Image]:
        return list(self._images.values())

    def delete_image(self, image_name: str, tag: str) -> bool:
        key = f"{image_name}:{tag}"
        if key in self._images:
            del self._images[key]
            return True
        return False


_registry: Optional[ContainerRegistry] = None


def get_registry() -> ContainerRegistry:
    global _registry
    if _registry is None:
        _registry = ContainerRegistry(
            config=RegistryConfig(
                provider=RegistryProvider.GITHUB_CR,
                url="ghcr.io",
                namespace="astrovoxai",
            )
        )
    return _registry
