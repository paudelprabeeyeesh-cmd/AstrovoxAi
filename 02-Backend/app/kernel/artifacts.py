"""Universal artifact system for the DMIE."""

from __future__ import annotations

import base64
import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .bus import get_event_bus


class ArtifactType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    WORKFLOW = "workflow"
    MEMORY = "memory"
    TOOL_RESULT = "tool_result"
    AGENT_OUTPUT = "agent_output"
    SEARCH_RESULT = "search_result"
    CHAT = "chat"
    PLUGIN_RESULT = "plugin_result"


@dataclass
class Artifact:
    """Universal artifact type for every modality and subsystem."""

    id: str
    type: ArtifactType
    content: Any
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    owner_id: str = "anonymous"
    workspace_id: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    version: int = 1
    parent_id: Optional[str] = None
    content_hash: str = ""
    mime_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = self._hash_content()

    def _hash_content(self) -> str:
        try:
            if isinstance(self.content, str):
                payload = self.content.encode("utf-8")
            elif isinstance(self.content, bytes):
                payload = self.content
            else:
                payload = repr(self.content).encode("utf-8")
        except Exception:
            payload = b""
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "created_at": self.created_at,
            "owner_id": self.owner_id,
            "workspace_id": self.workspace_id,
            "metadata": self.metadata,
            "provenance": self.provenance,
            "version": self.version,
            "parent_id": self.parent_id,
            "content_hash": self.content_hash,
            "mime_type": self.mime_type,
        }


class ArtifactRegistry:
    """Stores artifacts and tracks their lineage."""

    def __init__(self) -> None:
        self._artifacts: Dict[str, Artifact] = {}
        self._by_type: Dict[ArtifactType, List[str]] = {}
        self._by_workspace: Dict[str, List[str]] = {}

    def register(self, artifact: Artifact) -> Artifact:
        self._artifacts[artifact.id] = artifact
        self._by_type.setdefault(artifact.type, []).append(artifact.id)
        self._by_workspace.setdefault(artifact.workspace_id, []).append(artifact.id)
        get_event_bus().publish(
            "artifact.registered",
            {"id": artifact.id, "type": artifact.type.value},
            source="kernel.artifact",
        )
        return artifact

    def derive(self, parent: Artifact, *, type: ArtifactType, content: Any, **metadata: Any) -> Artifact:
        child = Artifact(
            id=f"art_{uuid.uuid4().hex[:10]}",
            type=type,
            content=content,
            owner_id=parent.owner_id,
            workspace_id=parent.workspace_id,
            parent_id=parent.id,
            metadata=metadata.get("metadata", {}),
            provenance=[
                *parent.provenance,
                {"id": parent.id, "type": parent.type.value, "version": parent.version},
            ],
            version=parent.version + 1,
            mime_type=metadata.get("mime_type", "application/octet-stream"),
        )
        return self.register(child)

    def get(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)

    def list(
        self,
        type: Optional[ArtifactType] = None,
        workspace_id: Optional[str] = None,
    ) -> List[Artifact]:
        ids: List[str]
        if type is not None:
            ids = self._by_type.get(type, [])
        elif workspace_id is not None:
            ids = self._by_workspace.get(workspace_id, [])
        else:
            ids = list(self._artifacts.keys())
        return [self._artifacts[i] for i in ids if i in self._artifacts]

    def lineage(self, artifact_id: str) -> List[Artifact]:
        chain: List[Artifact] = []
        current = self._artifacts.get(artifact_id)
        while current is not None:
            chain.append(current)
            if current.parent_id is None:
                break
            current = self._artifacts.get(current.parent_id)
        return chain

    def stats(self) -> Dict[str, Any]:
        return {
            "total": len(self._artifacts),
            "by_type": {t.value: len(ids) for t, ids in self._by_type.items()},
            "workspaces": len(self._by_workspace),
        }


_GLOBAL_REGISTRY: Optional[ArtifactRegistry] = None


def get_artifact_registry() -> ArtifactRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ArtifactRegistry()
    return _GLOBAL_REGISTRY


def make_text_artifact(text: str, **kwargs: Any) -> Artifact:
    return Artifact(
        id=f"art_{uuid.uuid4().hex[:10]}",
        type=ArtifactType.TEXT,
        content=text,
        mime_type="text/plain",
        **kwargs,
    )


def make_chat_artifact(messages: List[Dict[str, Any]], **kwargs: Any) -> Artifact:
    return Artifact(
        id=f"art_{uuid.uuid4().hex[:10]}",
        type=ArtifactType.CHAT,
        content=messages,
        mime_type="application/json",
        **kwargs,
    )


def make_image_artifact(data: bytes, mime_type: str = "image/png", **kwargs: Any) -> Artifact:
    return Artifact(
        id=f"art_{uuid.uuid4().hex[:10]}",
        type=ArtifactType.IMAGE,
        content=base64.b64encode(data).decode("ascii"),
        mime_type=mime_type,
        **kwargs,
    )