from typing import Dict, Any, Optional, List
import time
from ASTROVOX_AI.ai_core.distributed.gpu_monitoring import GPUMonitor


class GPUAutoScaler:
    def __init__(self, min_gpus: int = 1, max_gpus: int = 8, scale_up_threshold: float = 0.8, scale_down_threshold: float = 0.3, cooldown_seconds: float = 60.0):
        self.min_gpus = min_gpus
        self.max_gpus = max_gpus
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.cooldown_seconds = cooldown_seconds
        self.current_gpus = min_gpus
        self.last_scale_time = 0.0
        self.monitor = GPUMonitor()

    def evaluate(self) -> Optional[int]:
        if self.current_gpus == 0:
            return None
        utilization = self.monitor.get_current_utilization(0).get('utilization', 0.0)
        now = time.time()
        if now - self.last_scale_time < self.cooldown_seconds:
            return None
        if utilization > self.scale_up_threshold and self.current_gpus < self.max_gpus:
            self.current_gpus += 1
            self.last_scale_time = now
            return self.current_gpus
        elif utilization < self.scale_down_threshold and self.current_gpus > self.min_gpus:
            self.current_gpus -= 1
            self.last_scale_time = now
            return self.current_gpus
        return None

    def get_current_replicas(self) -> int:
        return self.current_gpus
