from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class ModelEndpoint:
    model_id: str
    version: str
    endpoint_url: str
    replicas: int = 1


class ModelServing:
    def __init__(self):
        self.endpoints: Dict[str, ModelEndpoint] = {}

    def register(self, endpoint: ModelEndpoint) -> None:
        self.endpoints[endpoint.model_id] = endpoint

    def get_endpoint(self, model_id: str) -> ModelEndpoint:
        return self.endpoints.get(model_id)
