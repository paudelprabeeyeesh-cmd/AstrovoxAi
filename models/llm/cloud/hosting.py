import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class APIKey:
    key_id: str
    developer_id: str
    key_hash: str
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    is_active: bool = True


@dataclass
class HostedModel:
    model_id: str
    name: str
    owner_id: str
    endpoint: str
    replicas: int = 1
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class ModelHostingService:
    def __init__(self) -> None:
        self._models: Dict[str, HostedModel] = {}
        self._api_keys: Dict[str, APIKey] = {}
        self._request_log: List[Dict[str, Any]] = []

    def create_api_key(self, developer_id: str, name: str, key: str) -> APIKey:
        import hashlib
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        api_key = APIKey(
            key_id=str(uuid.uuid4()),
            developer_id=developer_id,
            key_hash=key_hash,
            name=name,
        )
        self._api_keys[api_key.key_id] = api_key
        logger.info("Created API key %s for developer %s", name, developer_id)
        return api_key

    def revoke_api_key(self, key_id: str) -> None:
        if key_id not in self._api_keys:
            raise KeyError(f"API key not found: {key_id}")
        self._api_keys[key_id].is_active = False
        logger.info("Revoked API key %s", key_id)

    def validate_api_key(self, key: str) -> Optional[APIKey]:
        import hashlib
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        for api_key in self._api_keys.values():
            if api_key.key_hash == key_hash and api_key.is_active:
                api_key.last_used_at = datetime.utcnow()
                return api_key
        return None

    def host_model(
        self,
        name: str,
        owner_id: str,
        endpoint: str,
        replicas: int = 1,
    ) -> HostedModel:
        model_id = str(uuid.uuid4())
        hosted = HostedModel(
            model_id=model_id,
            name=name,
            owner_id=owner_id,
            endpoint=endpoint,
            replicas=replicas,
        )
        self._models[model_id] = hosted
        logger.info("Hosted model %s at %s", name, endpoint)
        return hosted

    def update_replicas(self, model_id: str, replicas: int) -> HostedModel:
        if model_id not in self._models:
            raise KeyError(f"Model not found: {model_id}")
        self._models[model_id].replicas = replicas
        return self._models[model_id]

    def log_request(
        self,
        model_id: str,
        developer_id: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
    ) -> Dict[str, Any]:
        entry = {
            "request_id": str(uuid.uuid4()),
            "model_id": model_id,
            "developer_id": developer_id,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._request_log.append(entry)
        return entry

    def get_hosted_model(self, model_id: str) -> HostedModel:
        if model_id not in self._models:
            raise KeyError(f"Model not found: {model_id}")
        return self._models[model_id]

    def list_hosted_models(self) -> List[HostedModel]:
        return list(self._models.values())
