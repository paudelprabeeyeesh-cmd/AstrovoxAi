import os
from typing import List, Optional
import torch
import torch.distributed as dist
import torch.multiprocessing as mp


class NCCLBackend:
    def __init__(self, world_size: int, device_ids: Optional[List[int]] = None):
        self.world_size = world_size
        self.device_ids = device_ids or list(range(world_size))
        self.initialized = False

    def init_process_group(self, rank: int, master_addr: str = 'localhost', master_port: str = '29500') -> None:
        os.environ['MASTER_ADDR'] = master_addr
        os.environ['MASTER_PORT'] = master_port
        dist.init_process_group(backend='nccl', rank=rank, world_size=self.world_size)
        self.initialized = True

    def all_reduce(self, tensor: torch.Tensor, op: str = 'sum') -> None:
        if not self.initialized:
            raise RuntimeError('NCCL backend not initialized')
        dist.all_reduce(tensor, op=getattr(dist.ReduceOp, op.upper()))

    def all_gather(self, tensor_list: List[torch.Tensor], tensor: torch.Tensor) -> None:
        if not self.initialized:
            raise RuntimeError('NCCL backend not initialized')
        dist.all_gather(tensor_list, tensor)

    def broadcast(self, tensor: torch.Tensor, src: int = 0) -> None:
        if not self.initialized:
            raise RuntimeError('NCCL backend not initialized')
        dist.broadcast(tensor, src=src)

    def barrier(self) -> None:
        if not self.initialized:
            raise RuntimeError('NCCL backend not initialized')
        dist.barrier()

    def cleanup(self) -> None:
        if self.initialized:
            dist.destroy_process_group()
            self.initialized = False
