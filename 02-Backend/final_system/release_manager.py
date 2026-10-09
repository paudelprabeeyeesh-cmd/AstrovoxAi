"""
Manages release lifecycle and environment promotion.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class ReleaseStatus(Enum):
    DRAFT = auto()
    STAGED = auto()
    RELEASED = auto()
    DEPRECATED = auto()


@dataclass
class Release:
    version: str
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ReleaseStatus = ReleaseStatus.DRAFT


class ReleaseManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._releases: Dict[str, Release] = {}

    def create_release(self, version: str, artifacts: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> Release:
        release = Release(version=version, artifacts=artifacts or [], metadata=metadata or {})
        with self._lock:
            self._releases[version] = release
        return release

    def promote(self, version: str, status: ReleaseStatus) -> Release:
        with self._lock:
            release = self._releases.get(version)
        if not release:
            raise KeyError(f"release not found: {version}")
        release.status = status
        return release

    def get_release(self, version: str) -> Release:
        with self._lock:
            release = self._releases.get(version)
        if not release:
            raise KeyError(f"release not found: {version}")
        return release

    def list_releases(self) -> List[str]:
        with self._lock:
            return list(self._releases.keys())
