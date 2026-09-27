"""AI edge inference."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIEdgeModel:
    model_id: str
    name: str
    size_bytes: int
    format: str
    loaded: bool = False


class AIEdgeInference:
    def __init__(self) -> None:
        self._models: Dict[str, AIEdgeModel] = {}

    def load_model(self, model: AIEdgeModel) -> None:
        model.loaded = True
        self._models[model.model_id] = model

    async def infer(self, model_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        model = self._models.get(model_id)
        if not model or not model.loaded:
            raise ValueError("model not loaded")
        return {"model_id": model_id, "output": []}


ai_edge_inference = AIEdgeInference()
