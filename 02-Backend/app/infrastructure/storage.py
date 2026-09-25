"""Storage management."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class StorageType(Enum):
    BLOCK = "block"
    OBJECT = "object"
    FILE = "file"
    CACHE = "cache"


class StorageTier(Enum):
    STANDARD = "standard"
    INFREQUENT = "infrequent_access"
    ARCHIVE = "archive"
    GLACIER = "glacier"


@dataclass
class StorageVolume:
    volume_id: str
    name: str
    storage_type: StorageType
    size_gb: int
    tier: StorageTier = StorageTier.STANDARD
    encrypted: bool = True
    region: str = "us-east-1"
    provider: str = "aws"
    metadata: Dict[str, Any] = field(default_factory=dict)


class StorageManager:
    _volumes: Dict[str, StorageVolume] = {}

    @classmethod
    def create_volume(cls, volume: StorageVolume) -> StorageVolume:
        cls._volumes[volume.volume_id] = volume
        return volume

    @classmethod
    def get_volume(cls, volume_id: str) -> Optional[StorageVolume]:
        return cls._volumes.get(volume_id)

    @classmethod
    def list_volumes(cls) -> List[StorageVolume]:
        return list(cls._volumes.values())
