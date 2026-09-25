"""
Artifacts and canvas for displaying code, documents, and interactive content.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ArtifactType(str, Enum):
    CODE = "code"
    DOCUMENT = "document"
    MARKDOWN = "markdown"
    HTML = "html"
    SVG = "svg"
    MERMAID = "mermaid"
    REACT = "react"


@dataclass
class Artifact:
    artifact_id: str
    type: ArtifactType
    title: str
    content: str
    language: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "type": self.type.value,
            "title": self.title,
            "content": self.content,
            "language": self.language,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ArtifactManager:
    """Manage artifacts for code, documents, and interactive content."""

    def __init__(self):
        self.artifacts: Dict[str, Artifact] = {}
        self.conversation_artifacts: Dict[str, List[str]] = {}

    def create_artifact(self, artifact_type: ArtifactType, title: str, content: str, language: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, conversation_id: Optional[str] = None) -> Artifact:
        artifact_id = f"artifact_{int(time.time() * 1000)}"
        artifact = Artifact(artifact_id=artifact_id, type=artifact_type, title=title, content=content, language=language, metadata=metadata or {})
        self.artifacts[artifact_id] = artifact
        if conversation_id:
            self.conversation_artifacts.setdefault(conversation_id, []).append(artifact_id)
        return artifact

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        return self.artifacts.get(artifact_id)

    def update_artifact(self, artifact_id: str, content: str, title: Optional[str] = None) -> Optional[Artifact]:
        artifact = self.artifacts.get(artifact_id)
        if artifact:
            artifact.content = content
            if title:
                artifact.title = title
            artifact.updated_at = time.time()
        return artifact

    def delete_artifact(self, artifact_id: str) -> bool:
        return self.artifacts.pop(artifact_id, None) is not None

    def get_conversation_artifacts(self, conversation_id: str) -> List[Artifact]:
        artifact_ids = self.conversation_artifacts.get(conversation_id, [])
        return [self.artifacts[aid] for aid in artifact_ids if aid in self.artifacts]

    def create_code_artifact(self, code: str, language: str, title: str = "Code") -> Artifact:
        return self.create_artifact(ArtifactType.CODE, title=title, content=code, language=language)

    def create_html_artifact(self, html: str, title: str = "HTML") -> Artifact:
        return self.create_artifact(ArtifactType.HTML, title=title, content=html, language="html")

    def create_svg_artifact(self, svg: str, title: str = "SVG") -> Artifact:
        return self.create_artifact(ArtifactType.SVG, title=title, content=svg, language="svg")


artifact_manager = ArtifactManager()
