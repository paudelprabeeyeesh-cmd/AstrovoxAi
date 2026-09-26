"""Model registry for versioning and lifecycle management."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelStage(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


@dataclass
class ModelVersion:
    model_id: str
    version: str
    stage: ModelStage
    artifact_path: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    promoted_at: Optional[datetime] = None


class ModelRegistry:
    def __init__(self) -> None:
        self._models: Dict[str, Dict[str, ModelVersion]] = {}

    def register(self, model_id: str, version: str, artifact_path: str, stage: ModelStage = ModelStage.DEVELOPMENT) -> ModelVersion:
        if model_id not in self._models:
            self._models[model_id] = {}
        mv = ModelVersion(model_id=model_id, version=version, stage=stage, artifact_path=artifact_path)
        self._models[model_id][version] = mv
        return mv

    def promote(self, model_id: str, version: str, stage: ModelStage) -> Optional[ModelVersion]:
        mv = self._models.get(model_id, {}).get(version)
        if mv:
            mv.stage = stage
            mv.promoted_at = datetime.now(timezone.utc)
        return mv

    def get_versions(self, model_id: str, stage: Optional[ModelStage] = None) -> List[ModelVersion]:
        versions = list(self._models.get(model_id, {}).values())
        if stage:
            versions = [v for v in versions if v.stage == stage]
        return sorted(versions, key=lambda v: v.created_at, reverse=True)


model_registry = ModelRegistry()
