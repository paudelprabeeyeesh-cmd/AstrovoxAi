from typing import Dict, Any, Optional, List
import time
import threading
import torch
import torch.cuda as cuda


class GPUMonitor:
    def __init__(self, device_ids: Optional[List[int]] = None, interval: float = 1.0):
        self.device_ids = device_ids or list(range(torch.cuda.device_count()))
        self.interval = interval
        self.running = False
        self.history: Dict[int, List[Dict[str, Any]]] = {i: [] for i in self.device_ids}
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join()

    def _monitor_loop(self) -> None:
        while self.running:
            for gpu_id in self.device_ids:
                if gpu_id < cuda.device_count():
                    allocated = cuda.memory_allocated(gpu_id)
                    reserved = cuda.memory_reserved(gpu_id)
                    total = cuda.get_device_properties(gpu_id).total_memory
                    self.history[gpu_id].append({'time': time.time(), 'allocated': allocated, 'reserved': reserved, 'total': total})
            time.sleep(self.interval)

    def get_current_utilization(self, gpu_id: int) -> Dict[str, Any]:
        allocated = cuda.memory_allocated(gpu_id)
        total = cuda.get_device_properties(gpu_id).total_memory
        return {'allocated': allocated, 'total': total, 'utilization': allocated / total}

    def get_history(self, gpu_id: int) -> List[Dict[str, Any]]:
        return self.history.get(gpu_id, [])
