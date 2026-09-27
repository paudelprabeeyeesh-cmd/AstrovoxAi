"""Model management service."""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

models: Dict[str, Dict[str, Any]] = {}


class ModelManagementService:
    def list_models(self) -> List[Dict[str, Any]]:
        return list(models.values())

    def create_model(self, name: str, description: str = ""):
        model_id = f"model-{len(models) + 1}"
        models[model_id] = {
            "id": model_id,
            "name": name,
            "description": description,
            "status": "inactive",
        }
        return models[model_id]


model_management_service = ModelManagementService()
