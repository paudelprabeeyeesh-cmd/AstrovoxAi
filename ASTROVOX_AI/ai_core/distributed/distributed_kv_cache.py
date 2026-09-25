from typing import Optional, Dict, Any, List, Tuple
import torch
from ASTROVOX_AI.ai_core.inference.prefix_caching import PrefixCache


class DistributedKVCache:
    def __init__(self, num_nodes: int, max_seq_len: int, num_layers: int, num_heads: int, head_dim: int, device_ids: Optional[List[int]] = None):
        self.num_nodes = num_nodes
        self.max_seq_len = max_seq_len
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.device_ids = device_ids or list(range(num_nodes))
        self.node_caches: List[Dict[str, Any]] = [{} for _ in range(num_nodes)]
        self.global_cache = PrefixCache(max_size=1000)

    def get(self, key: str, node_id: int) -> Optional[Tuple[torch.Tensor, torch.Tensor, int]]:
        if key in self.node_caches[node_id]:
            return self.node_caches[node_id][key]
        return self.global_cache.get(key)

    def put(self, key: str, k: torch.Tensor, v: torch.Tensor, length: int, node_id: int) -> None:
        self.node_caches[node_id][key] = (k, v, length)
        self.global_cache.put(key, k, v, length)

    def broadcast(self, src_node: int, key: str) -> None:
        data = self.node_caches[src_node].get(key)
        if data:
            for i in range(self.num_nodes):
                if i != src_node:
                    self.node_caches[i][key] = data

    def clear_node(self, node_id: int) -> None:
        self.node_caches[node_id].clear()
