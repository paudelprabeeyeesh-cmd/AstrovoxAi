"""Artifact management for releases."""
from __future__ import annotations

import hashlib
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Artifact:
    artifact_id: str
    name: str
    version: str
    path: str
    checksum: str
    size_bytes: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ArtifactManager:
    def __init__(self, storage_dir: str = "/tmp/astrovox_artifacts"):
        self.storage_dir = storage_dir
        self._artifacts: Dict[str, Artifact] = {}
        os.makedirs(storage_dir, exist_ok=True)

    def store(self, name: str, version: str, data: bytes) -> Artifact:
        artifact_id = uuid.uuid4().hex
        path = os.path.join(self.storage_dir, f"{name}-{version}-{artifact_id}")
        with open(path, "wb") as f:
            f.write(data)
        checksum = hashlib.sha256(data).hexdigest()
        artifact = Artifact(
            artifact_id=artifact_id,
            name=name,
            version=version,
            path=path,
            checksum=checksum,
            size_bytes=len(data),
        )
        self._artifacts[artifact_id] = artifact
        return artifact

    def get(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)


artifact_manager = ArtifactManager()
