from typing import List
import torch
import torch.cuda as cuda


class CUDAMemoryAllocator:
    def __init__(self, device: int = 0):
        self.device = device
        self.allocated_memory: List[torch.Tensor] = []
        self.total_allocated = 0

    def allocate(self, shape: tuple, dtype: torch.dtype = torch.float32) -> torch.Tensor:
        tensor = torch.empty(shape, dtype=dtype, device=f'cuda:{self.device}')
        self.allocated_memory.append(tensor)
        self.total_allocated += tensor.numel() * tensor.element_size()
        return tensor

    def free(self, tensor: torch.Tensor) -> None:
        if tensor in self.allocated_memory:
            self.allocated_memory.remove(tensor)
            self.total_allocated -= tensor.numel() * tensor.element_size()
            del tensor
            cuda.empty_cache()

    def get_memory_info(self) -> Dict[str, int]:
        return {'allocated': cuda.memory_allocated(self.device), 'reserved': cuda.memory_reserved(self.device), 'total_allocated_by_manager': self.total_allocated}

    def clear(self) -> None:
        for tensor in self.allocated_memory:
            del tensor
        self.allocated_memory.clear()
        self.total_allocated = 0
        cuda.empty_cache()

    def memory_summary(self) -> str:
        info = self.get_memory_info()
        return f"Allocated: {info['allocated'] / 1e9:.2f} GB, Reserved: {info['reserved'] / 1e9:.2f} GB, Managed: {info['total_allocated_by_manager'] / 1e9:.2f} GB"
