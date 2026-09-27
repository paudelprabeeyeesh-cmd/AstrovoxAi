"""AI API versioning."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIVersionedAPI:
    api_id: str
    path: str
    version: str
    deprecated: bool = False


class AIAPIVersionManager:
    def __init__(self) -> None:
        self._apis: Dict[str, AIVersionedAPI] = {}

    def register(self, api: AIVersionedAPI) -> None:
        api.api_id = api.api_id or uuid.uuid4().hex
        self._apis[api.api_id] = api

    def get_by_path(self, path: str, version: str) -> Optional[AIVersionedAPI]:
        for api in self._apis.values():
            if api.path == path and api.version == version:
                return api
        return None


ai_api_version_manager = AIAPIVersionManager()
