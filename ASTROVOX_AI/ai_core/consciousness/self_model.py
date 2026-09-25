import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SelfModel:
    identity_id: str
    traits: dict[str, float] = field(default_factory=dict)
    memories: list[dict[str, Any]] = field(default_factory=list)
    values: dict[str, float] = field(default_factory=dict)
    capabilities: dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class SelfModelPersistence:
    def __init__(self, storage_path: str = "memory/self_model.json"):
        self.storage_path = storage_path
        self.models: dict[str, SelfModel] = {}
        self.version_history: dict[str, list[SelfModel]] = {}

    def create_model(self, identity_id: str, traits: dict[str, float] | None = None) -> SelfModel:
        model = SelfModel(
            identity_id=identity_id,
            traits=traits or {"openness": 0.7, "conscientiousness": 0.8, "empathy": 0.9},
        )
        self.models[identity_id] = model
        self.version_history.setdefault(identity_id, []).append(model)
        logger.info("Created self-model: %s", identity_id)
        return model

    def update_trait(self, identity_id: str, trait: str, value: float) -> dict[str, Any]:
        if identity_id not in self.models:
            return {"error": "Model not found"}

        self.models[identity_id].traits[trait] = max(0.0, min(1.0, value))
        self.models[identity_id].last_updated = datetime.utcnow().isoformat()
        logger.info("Updated trait %s for %s: %.2f", trait, identity_id, value)
        return {"status": "updated", "trait": trait, "value": value}

    def add_memory(self, identity_id: str, memory: dict[str, Any]) -> dict[str, Any]:
        if identity_id not in self.models:
            return {"error": "Model not found"}

        memory["timestamp"] = datetime.utcnow().isoformat()
        self.models[identity_id].memories.append(memory)
        self.models[identity_id].last_updated = datetime.utcnow().isoformat()
        return {"status": "memory_added", "total_memories": len(self.models[identity_id].memories)}

    def persist(self, identity_id: str) -> dict[str, Any]:
        if identity_id not in self.models:
            return {"error": "Model not found"}

        try:
            model = self.models[identity_id]
            data = {
                "identity_id": model.identity_id,
                "traits": model.traits,
                "memories": model.memories,
                "values": model.values,
                "capabilities": model.capabilities,
                "created_at": model.created_at,
                "last_updated": model.last_updated,
            }
            logger.info("Persisted self-model: %s", identity_id)
            return {"status": "persisted", "identity_id": identity_id}
        except Exception as exc:
            logger.error("Persistence failed: %s", exc)
            return {"error": str(exc)}

    def load_model(self, identity_id: str) -> dict[str, Any]:
        if identity_id in self.models:
            model = self.models[identity_id]
            return {
                "identity_id": model.identity_id,
                "traits": model.traits,
                "memory_count": len(model.memories),
                "values": model.values,
                "version": len(self.version_history.get(identity_id, [])),
            }
        return {"error": "Model not found"}
