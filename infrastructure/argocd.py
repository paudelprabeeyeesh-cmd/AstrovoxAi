"""ArgoCD GitOps configuration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ArgoCDApplication:
    app_id: str
    name: str
    repo_url: str
    path: str
    target_revision: str = "main"
    status: str = "synced"


class ArgoCDManager:
    def __init__(self) -> None:
        self._apps: Dict[str, ArgoCDApplication] = {}

    def register_application(self, app: ArgoCDApplication) -> None:
        self._apps[app.app_id] = app

    def get_application(self, app_id: str) -> Optional[ArgoCDApplication]:
        return self._apps.get(app_id)


argocd_manager = ArgoCDManager()
