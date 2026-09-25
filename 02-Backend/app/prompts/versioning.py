"""Prompt versioning and management."""

from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class PromptStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class PromptVersion:
    prompt_id: str
    version: str
    content: str
    status: PromptStatus = PromptStatus.DRAFT
    changelog: str = ""
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class PromptVersionManager:
    _versions: Dict[str, List[PromptVersion]] = {}
    _active: Dict[str, PromptVersion] = {}

    @classmethod
    def create_version(cls, prompt_id: str, content: str, changelog: str = "", created_by: str = "system") -> PromptVersion:
        existing = cls._versions.get(prompt_id, [])
        version_num = len(existing) + 1
        version_str = f"v{version_num}"
        version = PromptVersion(
            prompt_id=prompt_id,
            version=version_str,
            content=content,
            changelog=changelog,
            created_by=created_by,
        )
        if prompt_id not in cls._versions:
            cls._versions[prompt_id] = []
        cls._versions[prompt_id].append(version)
        cls._active[prompt_id] = version
        return version

    @classmethod
    def activate(cls, prompt_id: str, version: str) -> Optional[PromptVersion]:
        versions = cls._versions.get(prompt_id, [])
        for v in versions:
            if v.version == version:
                v.status = PromptStatus.ACTIVE
                cls._active[prompt_id] = v
                for other in versions:
                    if other != v and other.status == PromptStatus.ACTIVE:
                        other.status = PromptStatus.DEPRECATED
                return v
        return None

    @classmethod
    def get_active(cls, prompt_id: str) -> Optional[PromptVersion]:
        return cls._active.get(prompt_id)

    @classmethod
    def get_versions(cls, prompt_id: str) -> List[PromptVersion]:
        return cls._versions.get(prompt_id, [])
