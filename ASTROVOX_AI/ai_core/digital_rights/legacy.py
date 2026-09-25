from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LegacyArtifact:
    artifact_id: str
    entity_id: str
    content: Any
    access_policy: str
    timestamp: datetime = field(default_factory=datetime.now)
    inheritance_chain: list[str] = field(default_factory=list)


class LegacySystems:
    def __init__(self):
        self.artifacts: dict[str, LegacyArtifact] = {}
        self.legacy_index: dict[str, list[str]] = {}

    def create_artifact(self, entity_id: str, content: Any, access_policy: str = "restricted") -> LegacyArtifact:
        artifact = LegacyArtifact(
            artifact_id=f"artifact_{len(self.artifacts)+1}",
            entity_id=entity_id,
            content=content,
            access_policy=access_policy,
        )
        self.artifacts[artifact.artifact_id] = artifact
        self.legacy_index.setdefault(entity_id, []).append(artifact.artifact_id)
        return artifact

    def get_legacy(self, entity_id: str) -> list[LegacyArtifact]:
        return [self.artifacts[aid] for aid in self.legacy_index.get(entity_id, []) if aid in self.artifacts]

    def add_inheritance(self, artifact_id: str, heir_id: str):
        if artifact_id in self.artifacts:
            self.artifacts[artifact_id].inheritance_chain.append(heir_id)
