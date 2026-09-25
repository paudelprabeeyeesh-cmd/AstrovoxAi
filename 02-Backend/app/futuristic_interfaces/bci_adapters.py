import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class BCIDevice:
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_type: str = "eeg"
    sample_rate_hz: float = 250.0
    channels: list[str] = field(default_factory=list)
    status: str = "connected"
    connected_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class BCIAdapterRegistry:
    def __init__(self) -> None:
        self._devices: dict[str, BCIDevice] = {}

    def connect(self, device_id: str, device_type: str, sample_rate_hz: float) -> dict[str, Any]:
        channels = self._default_channels(device_type)
        device = BCIDevice(
            device_id=device_id,
            device_type=device_type,
            sample_rate_hz=sample_rate_hz,
            channels=channels,
        )
        self._devices[device_id] = device
        logger.info("BCI device connected: device_id=%s type=%s", device_id, device_type)
        return {
            "device_id": device.device_id,
            "device_type": device.device_type,
            "sample_rate_hz": device.sample_rate_hz,
            "status": device.status,
            "channels": device.channels,
            "connected_at": device.connected_at,
        }

    def disconnect(self, device_id: str) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"device_id": device_id, "status": "not_found"}
        device.status = "disconnected"
        self._devices.pop(device_id, None)
        return {"device_id": device_id, "status": "disconnected"}

    def list_devices(self) -> list[dict[str, Any]]:
        return [
            {
                "device_id": d.device_id,
                "device_type": d.device_type,
                "sample_rate_hz": d.sample_rate_hz,
                "channels": d.channels,
                "status": d.status,
                "connected_at": d.connected_at,
            }
            for d in self._devices.values()
        ]

    def get_device(self, device_id: str) -> Optional[dict[str, Any]]:
        device = self._devices.get(device_id)
        if not device:
            return None
        return {
            "device_id": device.device_id,
            "device_type": device.device_type,
            "sample_rate_hz": device.sample_rate_hz,
            "channels": device.channels,
            "status": device.status,
            "connected_at": device.connected_at,
            "metadata": device.metadata,
        }

    def _default_channels(self, device_type: str) -> list[str]:
        if device_type.lower() == "eeg":
            return ["FP1", "FP2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2", "Fz", "Cz", "Pz", "Oz"]
        if device_type.lower() == "emg":
            return ["EMG1", "EMG2", "EMG3", "EMG4"]
        if device_type.lower() == "meg":
            return ["MEG1", "MEG2", "MEG3", "MEG4", "MEG5", "MEG6"]
        return ["CH1", "CH2", "CH3"]
