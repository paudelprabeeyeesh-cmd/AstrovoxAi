from typing import Dict, Any, Optional, List
import time
import torch
import torch.cuda as cuda


class GPUProfiler:
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self.events: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None

    def start(self) -> None:
        self.start_time = time.time()
        torch.cuda.synchronize(self.device_id)

    def stop(self) -> Dict[str, Any]:
        torch.cuda.synchronize(self.device_id)
        end_time = time.time()
        elapsed = end_time - self.start_time if self.start_time else 0.0
        memory_allocated = cuda.memory_allocated(self.device_id)
        memory_reserved = cuda.memory_reserved(self.device_id)
        return {'time_seconds': elapsed, 'memory_allocated_bytes': memory_allocated, 'memory_reserved_bytes': memory_reserved}

    def record_event(self, name: str, fn: callable, *args, **kwargs) -> Any:
        torch.cuda.synchronize(self.device_id)
        start = time.time()
        result = fn(*args, **kwargs)
        torch.cuda.synchronize(self.device_id)
        end = time.time()
        self.events.append({'name': name, 'time': end - start})
        return result

    def summary(self) -> str:
        lines = ['GPU Profiling Summary']
        for event in self.events:
            lines.append(f"{event['name']}: {event['time']:.4f}s")
        return '\n'.join(lines)

    def export_profile(self, path: str) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            for event in self.events:
                f.write(f"{event['name']},{event['time']}\n")
