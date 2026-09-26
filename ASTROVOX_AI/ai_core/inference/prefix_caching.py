from typing import Dict, Optional, Tuple
import torch


class PrefixCache:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Tuple[torch.Tensor, torch.Tensor, int]] = {}
        self.access_count: Dict[str, int] = {}

    def get(self, prefix_hash: str) -> Optional[Tuple[torch.Tensor, torch.Tensor, int]]:
        if prefix_hash in self.cache:
            self.access_count[prefix_hash] += 1
            return self.cache[prefix_hash]
        return None

    def put(self, prefix_hash: str, k: torch.Tensor, v: torch.Tensor, length: int) -> None:
        if len(self.cache) >= self.max_size:
            least_used = min(self.access_count, key=self.access_count.get)
            del self.cache[least_used]
            del self.access_count[least_used]
        self.cache[prefix_hash] = (k, v, length)
        self.access_count[prefix_hash] = 1

    def compute_prefix_hash(self, input_ids: torch.Tensor) -> str:
        return hash(tuple(input_ids[0, :32].cpu().tolist()))

    def clear(self) -> None:
        self.cache.clear()
        self.access_count.clear()
