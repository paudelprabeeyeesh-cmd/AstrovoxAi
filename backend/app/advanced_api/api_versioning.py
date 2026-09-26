"""API versioning management."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VersionedAPI:
    api_id: str
    path: str
    version: str
    deprecated: bool = False
    sunset_date: Optional[datetime] = None


class APIVersionManager:
    def __init__(self) -> None:
        self._apis: Dict[str, VersionedAPI] = {}

    def register(self, api: VersionedAPI) -> None:
        api.api_id = api.api_id or uuid.uuid4().hex
        self._apis[api.api_id] = api

    def get_by_path(self, path: str, version: str) -> Optional[VersionedAPI]:
        for api in self._apis.values():
            if api.path == path and api.version == version:
                return api
        return None

    def list_deprecated(self) -> List[VersionedAPI]:
        return [api for api in self._apis.values() if api.deprecated]


api_version_manager = APIVersionManager()
