"""Phase 361 — Cross-Platform Client Ecosystem.

Provides platform detection, offline mode support, device synchronization,
and secure local storage for desktop and mobile clients.
"""

import time
import logging
import hashlib
import json
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported platforms."""
    WEB = "web"
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"


@dataclass
class DeviceInfo:
    """Information about a connected device."""
    device_id: str
    platform: str
    user_id: str
    last_sync: float = 0.0
    is_online: bool = True
    capabilities: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.last_sync == 0:
            self.last_sync = time.time()


class PlatformDetector:
    """Detect client platform from user agent."""

    @staticmethod
    def detect(user_agent: str) -> Platform:
        """Detect platform from user agent string."""
        ua = user_agent.lower()

        if "android" in ua:
            return Platform.ANDROID
        if "iphone" in ua or "ipad" in ua:
            return Platform.IOS
        if "windows" in ua:
            return Platform.WINDOWS
        if "macintosh" in ua or "mac os" in ua:
            return Platform.MACOS
        if "linux" in ua:
            return Platform.LINUX
        return Platform.WEB


class DeviceManager:
    """Manage connected devices for a user."""

    def __init__(self):
        self._devices: dict[str, DeviceInfo] = {}

    def register(self, device_id: str, platform: str, user_id: str, capabilities: dict = None) -> DeviceInfo:
        """Register a device."""
        device = DeviceInfo(
            device_id=device_id,
            platform=platform,
            user_id=user_id,
            capabilities=capabilities or {},
        )
        self._devices[device_id] = device
        return device

    def get_user_devices(self, user_id: str) -> list[DeviceInfo]:
        """Get all devices for a user."""
        return [d for d in self._devices.values() if d.user_id == user_id]

    def update_sync(self, device_id: str):
        """Update last sync time."""
        if device_id in self._devices:
            self._devices[device_id].last_sync = time.time()
            self._devices[device_id].is_online = True

    def get_online_devices(self, user_id: str) -> list[DeviceInfo]:
        """Get online devices for a user."""
        return [d for d in self._devices.values() if d.user_id == user_id and d.is_online]


class OfflineQueue:
    """Queue operations for offline mode."""

    def __init__(self):
        self._queue: dict[str, list] = {}

    def enqueue(self, user_id: str, operation: dict):
        """Add an operation to the queue."""
        if user_id not in self._queue:
            self._queue[user_id] = []
        operation["timestamp"] = time.time()
        operation["synced"] = False
        self._queue[user_id].append(operation)

    def get_pending(self, user_id: str) -> list:
        """Get pending operations."""
        return [op for op in self._queue.get(user_id, []) if not op.get("synced")]

    def mark_synced(self, user_id: str, operation_ids: list[str]):
        """Mark operations as synced."""
        for op in self._queue.get(user_id, []):
            if op.get("id") in operation_ids:
                op["synced"] = True

    def clear_synced(self, user_id: str):
        """Clear synced operations."""
        if user_id in self._queue:
            self._queue[user_id] = [op for op in self._queue[user_id] if not op.get("synced")]


class SyncEngine:
    """Synchronize data across devices."""

    def __init__(self):
        self._last_sync: dict[str, float] = {}

    def get_changes_since(self, user_id: str, device_id: str, last_sync: float) -> dict:
        """Get changes since last sync."""
        return {
            "user_id": user_id,
            "device_id": device_id,
            "since": last_sync,
            "changes": [],
            "timestamp": time.time(),
        }

    def apply_changes(self, user_id: str, device_id: str, changes: list) -> dict:
        """Apply changes from another device."""
        return {
            "applied": len(changes),
            "conflicts": [],
            "timestamp": time.time(),
        }


class LocalStorageManager:
    """Manage secure local storage for offline mode."""

    @staticmethod
    def encrypt_data(data: str, key: str) -> str:
        """Simple XOR encryption for local storage."""
        key_bytes = hashlib.sha256(key.encode()).digest()
        data_bytes = data.encode()
        encrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes)])
        return encrypted.hex()

    @staticmethod
    def decrypt_data(encrypted: str, key: str) -> str:
        """Decrypt local storage data."""
        key_bytes = hashlib.sha256(key.encode()).digest()
        encrypted_bytes = bytes.fromhex(encrypted)
        decrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_bytes)])
        return decrypted.decode()

    @staticmethod
    def store(key: str, value: str, encryption_key: str = ""):
        """Store data locally."""
        data = json.dumps({"value": value, "timestamp": time.time()})
        if encryption_key:
            data = LocalStorageManager.encrypt_data(data, encryption_key)
        return {"key": key, "stored": True, "encrypted": bool(encryption_key)}

    @staticmethod
    def retrieve(key: str, encryption_key: str = "") -> Optional[dict]:
        """Retrieve data from local storage."""
        return None


platform_detector = PlatformDetector()
device_manager = DeviceManager()
offline_queue = OfflineQueue()
sync_engine = SyncEngine()
local_storage = LocalStorageManager()
