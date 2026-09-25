"""Device trust and fingerprinting."""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import hashlib
import secrets
import user_agents


@dataclass
class Device:
    device_id: str
    user_id: str
    fingerprint: str
    user_agent: str
    ip_address: str
    trusted: bool = False
    last_seen: datetime = None
    first_seen: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now(timezone.utc)
        if self.first_seen is None:
            self.first_seen = datetime.now(timezone.utc)
        if self.metadata is None:
            self.metadata = {}


class DeviceTrustManager:
    _devices: Dict[str, Device] = {}
    _user_devices: Dict[str, list[str]] = {}

    @classmethod
    def register_device(
        cls,
        user_id: str,
        user_agent: str,
        ip_address: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Device:
        fingerprint = cls._generate_fingerprint(user_agent, ip_address)
        device_id = hashlib.sha256(f"{user_id}:{fingerprint}".encode()).hexdigest()[:16]
        device = Device(
            device_id=device_id,
            user_id=user_id,
            fingerprint=fingerprint,
            user_agent=user_agent,
            ip_address=ip_address,
            metadata=metadata or {},
        )
        cls._devices[device_id] = device
        if user_id not in cls._user_devices:
            cls._user_devices[user_id] = []
        if device_id not in cls._user_devices[user_id]:
            cls._user_devices[user_id].append(device_id)
        return device

    @classmethod
    def trust_device(cls, device_id: str) -> None:
        device = cls._devices.get(device_id)
        if device:
            device.trusted = True

    @classmethod
    def is_trusted(cls, device_id: str) -> bool:
        device = cls._devices.get(device_id)
        return device.trusted if device else False

    @classmethod
    def get_user_devices(cls, user_id: str) -> list[Device]:
        device_ids = cls._user_devices.get(user_id, [])
        return [cls._devices[did] for did in device_ids if did in cls._devices]

    @classmethod
    def _generate_fingerprint(cls, user_agent: str, ip_address: str) -> str:
        raw = f"{user_agent}:{ip_address}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]
