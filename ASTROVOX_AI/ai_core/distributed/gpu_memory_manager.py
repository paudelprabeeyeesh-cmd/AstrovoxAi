from typing import Dict, Any, List, Optional
import torch
import torch.cuda as cuda
from collections import OrderedDict


class GPUMemoryManager:
    def __init__(self, device_id: int = 0):
        self.device_id = device_id
        self.allocated_tensors: OrderedDict[str, torch.Tensor] = OrderedDict()
        self.total_memory = cuda.get_device_properties(device_id).total_memory if cuda.is_available() else 0
        self.memory_limit = int(self.total_memory * 0.9)

    def allocate(self, name: str, shape: tuple, dtype: torch.dtype = torch.float32) -> torch.Tensor:
        tensor = torch.empty(shape, dtype=dtype, device=f'cuda:{self.device_id}')
        self.allocated_tensors[name] = tensor
        self._enforce_limit()
        return tensor

    def _enforce_limit(self) -> None:
        while self.get_allocated_memory() > self.memory_limit and self.allocated_tensors:
            oldest_name, oldest_tensor = self.allocated_tensors.popitem(last=False)
            del oldest_tensor
            cuda.empty_cache()

    def free(self, name: str) -> None:
        if name in self.allocated_tensors:
            del self.allocated_tensors[name]
            cuda.empty_cache()

    def get_allocated_memory(self) -> int:
        return sum(t.numel() * t.element_size() for t in self.allocated_tensors.values())

    def get_memory_info(self) -> Dict[str, int]:
        return {'total': self.total_memory, 'limit': self.memory_limit, 'allocated': self.get_allocated_memory(), 'free': self.total_memory - self.get_allocated_memory()}

    def clear(self) -> None:
        for name in list(self.allocated_tensors.keys()):
            self.free(name)
        self.allocated_tensors.clear()
