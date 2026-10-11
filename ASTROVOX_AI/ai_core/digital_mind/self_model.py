from dataclasses import dataclass, field
from datetime import datetime


class PersistentSelfModel:
    def __init__(self, identity: str = "digital_self"):
        self.model = PersistentSelfModel(
            identity=identity,
            personality_traits={
                "openness": 0.7,
                "conscientiousness": 0.8,
                "extraversion": 0.5,
                "agreeableness": 0.8,
                "neuroticism": 0.2,
            },
            memory_anchors=[],
            relationship_graph={},
            continuity_token="",
        )
        self.version_history: list[PersistentSelfModel] = []

    def update_trait(self, trait: str, value: float):
        self.model.personality_traits[trait] = max(0.0, min(1.0, value))
        self.model.version += 1
        self.model.updated_at = datetime.now()
        self.version_history.append(self.model)

    def add_memory_anchor(self, anchor: str):
        self.model.memory_anchors.append(anchor)
        if len(self.model.memory_anchors) > 100:
            self.model.memory_anchors = self.model.memory_anchors[-100:]

    def get_model(self) -> PersistentSelfModel:
        return self.model
