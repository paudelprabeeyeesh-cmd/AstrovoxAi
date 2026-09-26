"""Data lake storage abstraction."""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LakeObject:
    object_id: str
    path: str
    size_bytes: int
    content_type: str
    metadata: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataLake:
    def __init__(self, root_path: str = "/tmp/astrovox_datalake"):
        self.root_path = root_path
        self._objects: Dict[str, LakeObject] = {}
        os.makedirs(root_path, exist_ok=True)

    def put(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> LakeObject:
        object_id = uuid.uuid4().hex
        full_path = os.path.join(self.root_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)
        lake_object = LakeObject(object_id=object_id, path=path, size_bytes=len(data), content_type=content_type)
        self._objects[object_id] = lake_object
        return lake_object

    def get(self, object_id: str) -> Optional[bytes]:
        lake_object = self._objects.get(object_id)
        if not lake_object:
            return None
        full_path = os.path.join(self.root_path, lake_object.path)
        try:
            with open(full_path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def list_objects(self, prefix: str = "") -> List[LakeObject]:
        return [o for o in self._objects.values() if o.path.startswith(prefix)]


data_lake = DataLake()
