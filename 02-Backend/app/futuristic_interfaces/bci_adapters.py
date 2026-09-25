import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class BCIAdapterRegistry:
    def __init__(self) -> None:
        self._devices: dict[str, dict[str, Any]] = {}

    def connect(self, device_id: str, device_type: str, sample_rate_hz: float) -> dict[str, Any]:
        entry = {
            "device_id": device_id,
            "device_type": device_type,
            "sample_rate_hz": sample_rate_hz,
            "status": "connected",
            "channels": self._default_channels(device_type),
            "connected_at": logging.Formatter().formatTime(logging.LogRecord(
                name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
            )),
        }
        self._devices[device_id] = entry
        return entry

    def disconnect(self, device_id: str) -> dict[str, Any]:
        if device_id not in self._devices:
            return {"device_id": device_id, "status": "not_found"}
        entry = self._devices.pop(device_id)
        entry["status"] = "disconnected"
        return entry

    def list_devices(self) -> list[dict[str, Any]]:
        return list(self._devices.values())

    def _default_channels(self, device_type: str) -> list[str]:
        if device_type.lower() == "eeg":
            return ["FP1", "FP2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2", "Fz", "Cz", "Pz", "Oz"]
        if device_type.lower() == "emg":
            return ["EMG1", "EMG2", "EMG3", "EMG4"]
        if device_type.lower() == "meg":
            return ["MEG1", "MEG2", "MEG3", "MEG4", "MEG5", "MEG6"]
        return ["CH1", "CH2", "CH3"]
