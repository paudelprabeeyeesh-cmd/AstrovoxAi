from typing import Optional, Dict, Any, List
from ASTROVOX_AI.ai_core.distributed.gpu_auto_scaling import GPUAutoScaler
from ASTROVOX_AI.ai_core.distributed.gpu_monitoring import GPUMonitor


class AutoScaling:
    def __init__(self, min_replicas: int = 1, max_replicas: int = 10, target_cpu: float = 70.0, cooldown_seconds: float = 60.0):
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.target_cpu = target_cpu
        self.cooldown_seconds = cooldown_seconds
        self.current_replicas = min_replicas
        self.last_scale_time = 0.0
        self.monitor = GPUMonitor()
        self.gpu_scaler = GPUAutoScaler(min_gpus=min_replicas, max_gpus=max_replicas)

    def evaluate(self, current_metrics: Dict[str, float]) -> Optional[int]:
        cpu_util = current_metrics.get('cpu_percent', 0.0)
        gpu_util = current_metrics.get('gpu_utilization', 0.0)
        import time
        now = time.time()
        if now - self.last_scale_time < self.cooldown_seconds:
            return None
        if cpu_util > self.target_cpu or gpu_util > self.target_cpu:
            if self.current_replicas < self.max_replicas:
                self.current_replicas += 1
                self.last_scale_time = now
                return self.current_replicas
        elif cpu_util < self.target_cpu * 0.5 and gpu_util < self.target_cpu * 0.5:
            if self.current_replicas > self.min_replicas:
                self.current_replicas -= 1
                self.last_scale_time = now
                return self.current_replicas
        return None

    def get_replica_count(self) -> int:
        return self.current_replicas
