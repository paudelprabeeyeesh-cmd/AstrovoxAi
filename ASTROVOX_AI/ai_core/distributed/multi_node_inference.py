from typing import Optional, Dict, Any, List
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.distributed.multi_gpu_inference import MultiGPUInference
from ASTROVOX_AI.ai_core.distributed.distributed_kv_cache import DistributedKVCache


class MultiNodeInference:
    def __init__(self, model: nn.Module, num_nodes: int, gpus_per_node: int = 4, node_ids: Optional[List[int]] = None):
        self.num_nodes = num_nodes
        self.gpus_per_node = gpus_per_node
        self.node_ids = node_ids or list(range(num_nodes))
        self.node_engines: List[MultiGPUInference] = []
        for node_id in self.node_ids:
            device_ids = list(range(node_id * gpus_per_node, (node_id + 1) * gpus_per_node))
            self.node_engines.append(MultiGPUInference(model, device_ids=device_ids))
        self.kv_cache = DistributedKVCache(num_nodes, max_seq_len=2048, num_layers=12, num_heads=12, head_dim=64)

    def node_generate(self, node_id: int, input_ids: torch.Tensor, max_new_tokens: int = 100) -> torch.Tensor:
        engine = self.node_engines[node_id]
        return engine.infer(input_ids, max_new_tokens=max_new_tokens)

    def all_node_infer(self, input_ids: torch.Tensor, max_new_tokens: int = 100) -> List[torch.Tensor]:
        results = []
        for node_id, engine in enumerate(self.node_engines):
            result = self.node_generate(node_id, input_ids, max_new_tokens)
            results.append(result)
        return results

    def cleanup(self) -> None:
        for engine in self.node_engines:
            engine.cleanup()
