"""CPU/GPU workload balancer service wrapper."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ASTROVOX_AI.ai_core.inference.cpu_gpu_balancer import CPUGPUBalancer as CoreBalancer, DeviceStats as CoreDeviceStats

logger = logging.getLogger(__name__)


class CPUGPUBalancerService:
    def __init__(self, cpu_threshold: float = 80.0, gpu_threshold: float = 85.0):
        self._balancer = CoreBalancer(cpu_threshold=cpu_threshold, gpu_threshold=gpu_threshold)

    def start_monitoring(self, interval: float = 1.0) -> None:
        self._balancer.start_monitoring(interval=interval)

    def stop_monitoring(self) -> None:
        self._balancer.stop_monitoring()

    def decide_device(self, task_size: int = 1) -> str:
        return self._balancer.decide_device(task_size=task_size)

    def get_stats(self) -> Dict[str, Any]:
        return self._balancer.get_stats()
