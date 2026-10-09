"""
Artifacts - product_polish

Manage HTML/code artifacts with metadata.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Artifact:
    id: str
    title: str
    content: str
    artifact_type: str = "html"
    created_at: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if len(self.title) > 200:
            self.title = self.title[:200]
        if len(self.content) > 1_000_000:
            self.content = self.content[:1_000_000]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "artifact_type": self.artifact_type,
            "created_at": self.created_at,
            "meta": self.meta,
        }


class Artifacts:
    def __init__(self, max_artifacts: int = 50):
        self._artifacts: Dict[str, Artifact] = {}
        self.max_artifacts = max_artifacts

    def create(self, title: str, content: str, artifact_type: str = "html") -> Artifact:
        if len(self._artifacts) >= self.max_artifacts:
            oldest = min(self._artifacts.values(), key=lambda a: a.created_at)
            del self._artifacts[oldest.id]
        artifact = Artifact(id=str(uuid.uuid4()), title=title, content=content, artifact_type=artifact_type)
        self._artifacts[artifact.id] = artifact
        return artifact

    def get(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)

    def list_artifacts(self, limit: int = 50) -> List[Artifact]:
        items = sorted(self._artifacts.values(), key=lambda a: a.created_at, reverse=True)
        return items[:limit]

    def delete(self, artifact_id: str) -> bool:
        return self._artifacts.pop(artifact_id, None) is not None
