"""Container registry management."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RegistryProvider(Enum):
    DOCKER_HUB = "docker_hub"
    ECR = "ecr"
    GCR = "gcr"
    ACR = "acr"
    HARBOR = "harbor"
    QUAY = "quay"


@dataclass
class Image:
    image_id: str
    name: str
    tag: str
    digest: str
    size_mb: float
    registry: RegistryProvider
    pushed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegistryConfig:
    registry_id: str
    provider: RegistryProvider
    url: str
    username: str
    password: str
    namespace: str = "astrovox"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContainerRegistry:
    _images: Dict[str, Image] = {}
    _configs: Dict[str, RegistryConfig] = {}

    @classmethod
    def register_config(cls, config: RegistryConfig) -> None:
        cls._configs[config.registry_id] = config

    @classmethod
    def register_image(cls, image: Image) -> None:
        cls._images[image.image_id] = image

    @classmethod
    def get_images(cls, registry: Optional[RegistryProvider] = None, tag: Optional[str] = None) -> List[Image]:
        images = list(cls._images.values())
        if registry:
            images = [img for img in images if img.registry == registry]
        if tag:
            images = [img for img in images if img.tag == tag]
        return images
