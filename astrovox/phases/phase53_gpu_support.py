"""GPU acceleration support for Astrovox."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GPUPool:
    """A GPU pool."""
    device: str
    available: bool = False
    memory_mb: int = 0


class GPUSupport:
    """GPU acceleration support."""

    def __init__(self):
        self.devices: list[GPUPool] = []
        self.enabled = False

    def detect(self) -> bool:
        cuda = self._check_cuda()
        if cuda:
            self.devices.append(GPUPool(device="cuda:0", available=True, memory_mb=16384))
            self.enabled = True
        return self.enabled

    def _check_cuda(self) -> bool:
        return False

    def is_available(self) -> bool:
        return self.enabled

    def get_device(self) -> str | None:
        for d in self.devices:
            if d.available:
                return d.device
        return None

    def use(self, device: str) -> bool:
        for d in self.devices:
            if d.device == device:
                d.available = True
                self.enabled = True
                return True
        return False

    def memory_info(self) -> dict:
        return {"device_count": len(self.devices), "enabled": self.enabled}
