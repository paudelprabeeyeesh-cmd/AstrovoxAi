import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class SemanticCache:
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.model_versions = {}

    def _make_key(
        self, user_id: str, prompt_hash: str, model: str, shared: bool = False
    ) -> str:
        user_part = "shared" if shared else user_id
        key_data = f"{user_part}:{prompt_hash}:{model}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(
        self, user_id: str, prompt_hash: str, model: str, shared: bool = False
    ) -> dict | None:
        if not self.redis:
            return None

        key = self._make_key(user_id, prompt_hash, model, shared)
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    def set(
        self,
        user_id: str,
        prompt_hash: str,
        model: str,
        value: dict,
        ttl: int = 3600,
        shared: bool = False,
    ):
        if not self.redis:
            return

        key = self._make_key(user_id, prompt_hash, model, shared)
        self.redis.set(key, json.dumps(value), ex=ttl)

    def invalidate_model(self, model: str):
        if model in self.model_versions:
            del self.model_versions[model]

    def set_model_version(self, model: str, version: str):
        self.model_versions[model] = version

    def get_model_version(self, model: str) -> str | None:
        return self.model_versions.get(model)
