"""Internal Developer Platform (IDP) components."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ServiceTier(Enum):
    GOLDEN = "golden"
    SILVER = "silver"
    BRONZE = "bronze"
    CUSTOM = "custom"


@dataclass
class GoldenPath:
    path_id: str
    name: str
    description: str
    template_url: str
    language: str = "python"
    framework: str = "fastapi"
    required_services: List[str] = field(default_factory=list)
    estimated_time_minutes: int = 30


@dataclass
class ServiceTemplate:
    template_id: str
    name: str
    tier: ServiceTier
    language: str
    framework: str
    dependencies: List[str] = field(default_factory=list)
    ci_cd_config: Dict[str, Any] = field(default_factory=dict)
    monitoring_config: Dict[str, Any] = field(default_factory=dict)


class InternalDeveloperPlatform:
    _golden_paths: Dict[str, GoldenPath] = {}
    _templates: Dict[str, ServiceTemplate] = {}

    @classmethod
    def register_golden_path(cls, path: GoldenPath) -> None:
        cls._golden_paths[path.path_id] = path

    @classmethod
    def register_template(cls, template: ServiceTemplate) -> None:
        cls._templates[template.template_id] = template

    @classmethod
    def get_golden_path(cls, path_id: str) -> Optional[GoldenPath]:
        return cls._golden_paths.get(path_id)

    @classmethod
    def list_golden_paths(cls) -> List[GoldenPath]:
        return list(cls._golden_paths.values())
