from typing import Dict, Optional, List
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.distributed.nccl import NCCLBackend


class ShardedCheckpoint:
    def __init__(self, shard_count: int = 4, device_ids: Optional[List[int]] = None):
        self.shard_count = shard_count
        self.device_ids = device_ids or list(range(torch.cuda.device_count()))
        self.backend = NCCLBackend(shard_count, self.device_ids)
        self.shards: Dict[int, Dict[str, torch.Tensor]] = {i: {} for i in range(shard_count)}

    def shard_state_dict(self, state_dict: Dict[str, torch.Tensor]) -> Dict[int, Dict[str, torch.Tensor]]:
        keys = list(state_dict.keys())
        shard_size = len(keys) // self.shard_count
        for i in range(self.shard_count):
            start = i * shard_size
            end = start + shard_size if i < self.shard_count - 1 else len(keys)
            self.shards[i] = {k: state_dict[k] for k in keys[start:end]}
        return self.shards

    def load_shard(self, shard_id: int, path: str) -> None:
        self.shards[shard_id] = torch.load(path, map_location=f'cuda:{self.device_ids[shard_id % len(self.device_ids)]}')

    def save_shard(self, shard_id: int, path: str) -> None:
        torch.save(self.shards[shard_id], path)

    def merge_shards(self) -> Dict[str, torch.Tensor]:
        merged = {}
        for shard in self.shards.values():
            merged.update(shard)
        return merged

    def load_to_model(self, model: nn.Module, shard_paths: List[str]) -> nn.Module:
        for i, path in enumerate(shard_paths):
            self.load_shard(i, path)
        merged = self.merge_shards()
        model.load_state_dict(merged, strict=False)
        return model
