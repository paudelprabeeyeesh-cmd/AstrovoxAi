"""AI model registry."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AIModelStage(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


@dataclass
class AIModelVersion:
    model_id: str
    version: str
    stage: AIModelStage
    artifact_path: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AIModelRegistry:
    def __init__(self) -> None:
        self._models: Dict[str, Dict[str, AIModelVersion]] = {}

    def register(self, model_id: str, version: str, artifact_path: str, stage: AIModelStage = AIModelStage.DEVELOPMENT) -> AIModelVersion:
        if model_id not in self._models:
            self._models[model_id] = {}
        mv = AIModelVersion(model_id=model_id, version=version, stage=stage, artifact_path=artifact_path)
        self._models[model_id][version] = mv
        return mv

    def get_versions(self, model_id: str) -> List[AIModelVersion]:
        return list(self._models.get(model_id, {}).values())


ai_model_registry = AIModelRegistry()
