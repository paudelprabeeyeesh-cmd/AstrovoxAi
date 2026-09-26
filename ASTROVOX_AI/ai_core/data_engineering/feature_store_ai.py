"""AI feature store."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FeatureVector:
    feature_id: str
    values: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIFeatureStore:
    def __init__(self) -> None:
        self._features: Dict[str, FeatureVector] = {}

    def store(self, feature: FeatureVector) -> None:
        self._features[feature.feature_id] = feature

    def get(self, feature_id: str) -> Optional[FeatureVector]:
        return self._features.get(feature_id)


ai_feature_store = AIFeatureStore()
