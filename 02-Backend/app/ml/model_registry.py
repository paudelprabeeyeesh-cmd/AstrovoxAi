import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Model:
    model_id: str
    name: str
    version: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)
    stage: str = "development"
    registered_at: datetime = field(default_factory=datetime.utcnow)


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, dict[str, Model]] = {}
        self._counter: int = 0

    def register_model(self, name: str, version: str, path: str, metadata: dict[str, Any] | None = None) -> Model:
        self._counter += 1
        model = Model(model_id=f"model_{self._counter}", name=name, version=version, path=path, metadata=metadata or {})
        self._models.setdefault(name, {})[version] = model
        logger.info(f"Registered model {name} version {version} at {path}")
        return model

    def get_model(self, name: str, version: str) -> Model | None:
        return self._models.get(name, {}).get(version)

    def list_models(self) -> list[Model]:
        models: list[Model] = []
        for versions in self._models.values():
            models.extend(versions.values())
        return models

    def promote_model(self, model_id: str, stage: str) -> None:
        if stage not in {"development", "staging", "production"}:
            logger.error(f"Invalid stage {stage} for model {model_id}")
            return
        for versions in self._models.values():
            for model in versions.values():
                if model.model_id == model_id:
                    model.stage = stage
                    logger.info(f"Promoted model {model_id} to {stage}")
                    return
        logger.error(f"Model {model_id} not found")
