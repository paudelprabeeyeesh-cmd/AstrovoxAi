import logging
from typing import Any

logger = logging.getLogger(__name__)


class BCIApiStubService:
    def connect(self, device_id: str = "stub_device") -> dict[str, Any]:
        return {"status": "connected", "device_id": device_id}

    def disconnect(self, device_id: str = "stub_device") -> dict[str, Any]:
        return {"status": "disconnected", "device_id": device_id}

    def stream_signal(self, device_id: str = "stub_device") -> list[dict[str, Any]]:
        return [{"channel": "stub", "amplitude": 0.1, "frequency": 10.0}]
