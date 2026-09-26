"""Feature store for ML feature management."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Feature:
    feature_id: str
    name: str
    entity_id: str
    value: Any
    feature_type: str
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FeatureStore:
    def __init__(self) -> None:
        self._features: Dict[str, Feature] = {}
        self._entity_index: Dict[str, List[str]] = {}

    def add_feature(self, feature: Feature) -> None:
        self._features[feature.feature_id] = feature
        self._entity_index.setdefault(feature.entity_id, []).append(feature.feature_id)

    def get_features(self, entity_id: str, feature_names: Optional[List[str]] = None) -> List[Feature]:
        feature_ids = self._entity_index.get(entity_id, [])
        features = [self._features[fid] for fid in feature_ids if fid in self._features]
        if feature_names:
            features = [f for f in features if f.name in feature_names]
        return features

    def compute_feature(self, entity_id: str, name: str, func: Callable[[], Any]) -> Feature:
        feature_id = uuid.uuid4().hex
        feature = Feature(feature_id=feature_id, name=name, entity_id=entity_id, value=func(), feature_type="computed")
        self.add_feature(feature)
        return feature


feature_store = FeatureStore()
