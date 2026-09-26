"""CPU/GPU workload balancer for inference pipelines."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DeviceStats:
    device_type: str
    device_id: int
    utilization: float = 0.0
    memory_used: int = 0
    memory_total: int = 0
    temperature: float = 0.0
    power: float = 0.0


class CPUGPUBalancer:
    def __init__(self, cpu_threshold: float = 80.0, gpu_threshold: float = 85.0):
        self.cpu_threshold = cpu_threshold
        self.gpu_threshold = gpu_threshold
        self._lock = threading.RLock()
        self._cpu_stats: Optional[DeviceStats] = None
        self._gpu_stats: Dict[int, DeviceStats] = {}
        self._history: List[Dict[str, Any]] = []
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

    def start_monitoring(self, interval: float = 1.0) -> None:
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()
        logger.info("CPU/GPU balancer monitoring started")

    def stop_monitoring(self) -> None:
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _monitor_loop(self, interval: float) -> None:
        while self._running:
            try:
                self._refresh_stats()
            except Exception:
                logger.exception("Failed to refresh device stats")
            import time
            time.sleep(interval)

    def _refresh_stats(self) -> None:
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            self._cpu_stats = DeviceStats(
                device_type="cpu",
                device_id=0,
                utilization=cpu_percent,
                memory_used=int(mem.used),
                memory_total=int(mem.total),
            )
        except ImportError:
            self._cpu_stats = DeviceStats(device_type="cpu", device_id=0, utilization=0.0)
        try:
            import torch
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    util = torch.cuda.utilization(i)
                    mem_used, mem_total = torch.cuda.mem_get_info(i)
                    self._gpu_stats[i] = DeviceStats(
                        device_type="cuda",
                        device_id=i,
                        utilization=float(util),
                        memory_used=mem_total - mem_used,
                        memory_total=mem_total,
                    )
        except Exception:
            pass

    def decide_device(self, task_size: int = 1) -> str:
        with self._lock:
            cpu_ok = self._cpu_stats.utilization < self.cpu_threshold if self._cpu_stats else True
            gpu_ok = all(s.utilization < self.gpu_threshold for s in self._gpu_stats.values())
            gpu_mem_ok = all(s.memory_used < s.memory_total * 0.8 for s in self._gpu_stats.values())
            if self._gpu_stats and gpu_ok and gpu_mem_ok:
                return "cuda"
            if cpu_ok:
                return "cpu"
            if self._gpu_stats and gpu_ok:
                return "cuda"
            return "cpu"

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "cpu": self._cpu_stats.__dict__ if self._cpu_stats else None,
                "gpus": [s.__dict__ for s in self._gpu_stats.values()],
                "recommended_device": self.decide_device(),
            }
