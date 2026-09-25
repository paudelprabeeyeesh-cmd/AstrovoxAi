import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NeuralSignal:
    channel: str
    amplitude: float = 0.0
    frequency: float = 0.0
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BCIApiStub:
    def __init__(self, device_id: str = "stub_device"):
        self.device_id = device_id
        self.connected: bool = False

    def connect(self) -> dict[str, Any]:
        self.connected = True
        return {"status": "connected", "device_id": self.device_id}

    def disconnect(self) -> dict[str, Any]:
        self.connected = False
        return {"status": "disconnected"}

    def stream_signal(self) -> list[NeuralSignal]:
        return [NeuralSignal(channel="stub", amplitude=0.1, frequency=10.0)]
