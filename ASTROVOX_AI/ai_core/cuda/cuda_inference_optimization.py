import torch
import torch.nn as nn
from ASTROVOX_AI.ai_core.inference.kv_cache_compression import KVCacheCompressor
from ASTROVOX_AI.ai_core.inference.prefix_caching import PrefixCache
from ASTROVOX_AI.ai_core.cuda.cuda_graphs import CUDAGraphManager
from ASTROVOX_AI.ai_core.cuda.cuda_streams import CUDAStreamManager
from ASTROVOX_AI.ai_core.cuda.cuda_mixed_precision import CUDAMixedPrecision


class CUDAInferenceOptimizer:
    def __init__(self, model: nn.Module, device: int = 0, use_fp16: bool = True, use_kv_cache: bool = True, use_cuda_graphs: bool = True):
        self.model = model
        self.device = device
        self.use_fp16 = use_fp16
        self.use_kv_cache = use_kv_cache
        self.use_cuda_graphs = use_cuda_graphs
        self.mixed_precision = CUDAMixedPrecision(enabled=use_fp16)
        self.kv_compressor = KVCacheCompressor(compression_ratio=0.5)
        self.prefix_cache = PrefixCache(max_size=1000)
        self.stream_manager = CUDAStreamManager(num_streams=4, device=device)
        self.graph_manager = CUDAGraphManager(device=device)
        self.model.to(f'cuda:{device}')
        if use_fp16:
            self.model.half()

    def optimize_model(self) -> nn.Module:
        self.model = torch.jit.trace(self.model, torch.randn(1, 1, 768, device=f'cuda:{self.device}'))
        return self.model

    def capture_graph(self, dummy_input: torch.Tensor) -> None:
        self.graph_manager.capture_full_model(self.model, dummy_input, 'main')

    def replay_graph(self) -> None:
        self.graph_manager.replay('main')

    def warmup(self, dummy_input: torch.Tensor, num_warmup_steps: int = 10) -> None:
        for _ in range(num_warmup_steps):
            self.replay_graph() if self.use_cuda_graphs else self.mixed_precision.forward(self.model, dummy_input)
        torch.cuda.synchronize(self.device)

    def optimize_kv_cache(self, k: torch.Tensor, v: torch.Tensor) -> tuple:
        return self.kv_compressor.compress(k, v)
