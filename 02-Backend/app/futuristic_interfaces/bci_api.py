import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SignalStreamConfig:
    stream_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = "stub_device"
    sample_rate_hz: float = 250.0
    channels: list[str] = field(default_factory=lambda: ["stub"])
    buffer_size: int = 256
    timestamp: float = field(default_factory=time.time)


@dataclass
class SignalSample:
    sample_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stream_id: str = ""
    channel: str = "stub"
    amplitude: float = 0.0
    frequency_hz: float = 10.0
    timestamp: float = field(default_factory=time.time)


class BCIApiStubService:
    def __init__(self) -> None:
        self._streams: dict[str, SignalStreamConfig] = {}
        self._samples: dict[str, list[SignalSample]] = {}

    def connect(self, device_id: str = "stub_device") -> dict[str, Any]:
        stream = SignalStreamConfig(device_id=device_id)
        self._streams[stream.stream_id] = stream
        self._samples[stream.stream_id] = []
        logger.info("BCI stub connected: device_id=%s stream_id=%s", device_id, stream.stream_id)
        return {
            "status": "connected",
            "device_id": device_id,
            "stream_id": stream.stream_id,
            "sample_rate_hz": stream.sample_rate_hz,
            "channels": stream.channels,
        }

    def disconnect(self, device_id: str = "stub_device") -> dict[str, Any]:
        for stream_id, stream in list(self._streams.items()):
            if stream.device_id == device_id:
                self._streams.pop(stream_id, None)
                self._samples.pop(stream_id, None)
        return {"status": "disconnected", "device_id": device_id}

    def stream_signal(self, device_id: str = "stub_device") -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        for stream_id, stream in self._streams.items():
            if stream.device_id == device_id:
                for _ in range(stream.buffer_size):
                    sample = SignalSample(
                        stream_id=stream_id,
                        channel=stream.channels[0],
                        amplitude=0.1,
                        frequency_hz=10.0,
                    )
                    self._samples[stream_id].append(sample)
                    samples.append({
                        "sample_id": sample.sample_id,
                        "stream_id": sample.stream_id,
                        "channel": sample.channel,
                        "amplitude": sample.amplitude,
                        "frequency_hz": sample.frequency_hz,
                        "timestamp": sample.timestamp,
                    })
        if not samples:
            connected = self.connect(device_id)
            return [{"stream_id": connected["stream_id"], "status": "auto_connected"}]
        return samples

    def list_streams(self) -> list[dict[str, Any]]:
        return [
            {
                "stream_id": s.stream_id,
                "device_id": s.device_id,
                "sample_rate_hz": s.sample_rate_hz,
                "channels": s.channels,
            }
            for s in self._streams.values()
        ]
