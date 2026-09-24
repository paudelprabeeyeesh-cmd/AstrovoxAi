"""AI App Store with apps, integrations, and discovery."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AppStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


@dataclass
class AIApp:
    app_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    author_id: str = ""
    author_name: str = ""
    version: str = "1.0.0"
    manifest: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    status: AppStatus = AppStatus.PENDING
    install_count: int = 0
    rating: float = 0.0
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class AIAppStore:
    """App store for AI applications and integrations."""

    def __init__(self):
        self._apps: Dict[str, AIApp] = {}

    def submit(self, app: AIApp) -> AIApp:
        app.status = AppStatus.PENDING
        app.updated_at = time.time()
        self._apps[app.app_id] = app
        logger.info("App submitted: %s by %s", app.name, app.author_id)
        return app

    def approve(self, app_id: str) -> bool:
        app = self._apps.get(app_id)
        if not app:
            return False
        app.status = AppStatus.APPROVED
        app.updated_at = time.time()
        return True

    def reject(self, app_id: str) -> bool:
        app = self._apps.get(app_id)
        if not app:
            return False
        app.status = AppStatus.REJECTED
        app.updated_at = time.time()
        return True

    def get_app(self, app_id: str) -> Optional[AIApp]:
        return self._apps.get(app_id)

    def search(self, query: str, tags: Optional[List[str]] = None, limit: int = 20) -> List[AIApp]:
        results = []
        for app in self._apps.values():
            if app.status != AppStatus.APPROVED:
                continue
            if tags and not any(tag in app.tags for tag in tags):
                continue
            if query.lower() in app.name.lower() or query.lower() in app.description.lower():
                results.append(app)
        results.sort(key=lambda x: x.install_count, reverse=True)
        return results[:limit]

    def install(self, app_id: str, user_id: str) -> bool:
        app = self._apps.get(app_id)
        if not app or app.status != AppStatus.APPROVED:
            return False
        app.install_count += 1
        logger.info("App %s installed by %s", app.name, user_id)
        return True

    def list_approved(self) -> List[AIApp]:
        return [a for a in self._apps.values() if a.status == AppStatus.APPROVED]


ai_app_store = AIAppStore()
