"""Document collaboration with versioning."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentVersion:
    version_id: str
    document_id: str
    content: str
    author_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentCollaboration:
    def __init__(self) -> None:
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._versions: Dict[str, List[DocumentVersion]] = {}

    def create_document(self, title: str, owner_id: str) -> str:
        document_id = uuid.uuid4().hex
        self._documents[document_id] = {"title": title, "owner_id": owner_id}
        self._versions[document_id] = []
        return document_id

    def update(self, document_id: str, content: str, author_id: str) -> DocumentVersion:
        version = DocumentVersion(version_id=uuid.uuid4().hex, document_id=document_id, content=content, author_id=author_id)
        self._versions.setdefault(document_id, []).append(version)
        return version

    def get_versions(self, document_id: str) -> List[DocumentVersion]:
        return self._versions.get(document_id, [])


document_collaboration = DocumentCollaboration()
