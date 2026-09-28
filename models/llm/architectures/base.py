import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureSpec:
    name: str
    family: str
    paper: str
    description: str
    config_path: str
    parameter_formula: str
    key_innovations: list[str]
    supported_features: list[str]


class BaseArchitecture(ABC):
    @abstractmethod
    def build(self, config: Dict[str, Any]) -> nn.Module:
        pass

    @abstractmethod
    def count_parameters(self, config: Dict[str, Any]) -> int:
        pass

    @abstractmethod
    def get_spec(self) -> ArchitectureSpec:
        pass

    def validate_config(self, config: Dict[str, Any]) -> list[str]:
        return []

    def generate_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "architecture": self.get_spec().name,
            "parameters": self.count_parameters(config),
            "memory_mb": self.count_parameters(config) * 2 / (1024 * 1024),
            "config": config,
        }


class ArchitectureRegistry:
    _architectures: Dict[str, BaseArchitecture] = {}

    @classmethod
    def register(cls, name: str, architecture: BaseArchitecture):
        cls._architectures[name] = architecture
        logger.info("Registered architecture: %s", name)

    @classmethod
    def get(cls, name: str) -> Optional[BaseArchitecture]:
        return cls._architectures.get(name)

    @classmethod
    def list_architectures(cls) -> list[str]:
        return list(cls._architectures.keys())

    @classmethod
    def build(cls, name: str, config: Dict[str, Any]) -> nn.Module:
        arch = cls.get(name)
        if arch is None:
            raise ValueError(f"Unknown architecture: {name}. Available: {cls.list_architectures()}")
        return arch.build(config)

    @classmethod
    def compare(cls, configs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        results = {}
        for name, config in configs.items():
            arch = cls.get(name)
            if arch:
                results[name] = arch.generate_report(config)
        return results
