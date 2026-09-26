from typing import Optional, List
import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.distributed.multi_gpu_inference import MultiGPUInference
from ASTROVOX_AI.ai_core.inference.kv_cache_compression import KVCacheCompressor


class DistributedInference:
    def __init__(self, model: nn.Module, device_ids: Optional[List[int]] = None, use_kv_compression: bool = True):
        self.multi_gpu = MultiGPUInference(model, device_ids, use_tensor_parallel=True)
        self.kv_compressor = KVCacheCompressor(compression_ratio=0.5) if use_kv_compression else None
        self.device_ids = device_ids or list(range(torch.cuda.device_count()))

    def distributed_generate(self, input_ids: torch.Tensor, max_new_tokens: int = 100) -> torch.Tensor:
        batch_size = input_ids.shape[0]
        local_batch_size = batch_size // len(self.device_ids)
        results = []
        for i, device_id in enumerate(self.device_ids):
            device = torch.device(f'cuda:{device_id}')
            start_idx = i * local_batch_size
            end_idx = start_idx + local_batch_size if i < len(self.device_ids) - 1 else batch_size
            local_input = input_ids[start_idx:end_idx].to(device)
            local_output = self.multi_gpu.infer(local_input, max_new_tokens=max_new_tokens)
            results.append(local_output.cpu())
        return torch.cat(results, dim=0)

    def sharded_kv_inference(self, input_ids: torch.Tensor, k_cache: Optional[torch.Tensor] = None, v_cache: Optional[torch.Tensor] = None) -> tuple:
        local_input = input_ids.to(f'cuda:{self.device_ids[0]}')
        if k_cache is not None and self.kv_compressor:
            k_cache, v_cache = self.kv_compressor.compress(k_cache, v_cache)
        return self.multi_gpu.infer(local_input), k_cache, v_cache
