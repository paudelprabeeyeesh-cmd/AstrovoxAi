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


class LegacySystems:
    def __init__(self):
        self.artifacts: dict[str, LegacyArtifact] = {}

    def create_artifact(self, entity_id: str, content: Any, access_policy: str = "restricted") -> LegacyArtifact:
        artifact = LegacyArtifact(
            artifact_id=f"artifact_{len(self.artifacts)+1}",
            entity_id=entity_id,
            content=content,
            access_policy=access_policy,
        )
        self.artifacts[artifact.artifact_id] = artifact
        return artifact

    def get_legacy(self, entity_id: str) -> list[LegacyArtifact]:
        return [a for a in self.artifacts.values() if a.entity_id == entity_id]
