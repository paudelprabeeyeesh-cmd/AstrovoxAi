from typing import Optional, List
import torch
from ASTROVOX_AI.ai_core.distributed.nccl import NCCLBackend


class RingAllReduce:
    def __init__(self, world_size: int, device_ids: Optional[List[int]] = None):
        self.world_size = world_size
        self.backend = NCCLBackend(world_size, device_ids)

    def all_reduce(self, tensor: torch.Tensor, op: str = 'sum') -> torch.Tensor:
        self.backend.all_reduce(tensor, op)
        return tensor / self.world_size

    def reduce_scatter(self, tensor: torch.Tensor, output_list: List[torch.Tensor]) -> None:
        chunk_size = tensor.shape[0] // self.world_size
        for i in range(self.world_size):
            chunk = tensor[i * chunk_size:(i + 1) * chunk_size]
            output_list[i] = chunk.clone()
        self.backend.all_reduce(torch.stack(output_list))

    def all_gather(self, tensor: torch.Tensor) -> List[torch.Tensor]:
        gathered = [torch.zeros_like(tensor) for _ in range(self.world_size)]
        self.backend.all_gather(gathered, tensor)
        return gathered
