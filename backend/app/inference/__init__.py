"""Backend inference performance service layer."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.app.inference.async_scheduler import AsyncInferenceSchedulerService, Priority
from backend.app.inference.batching import DynamicBatchingService
from backend.app.inference.cpu_gpu_balancer import CPUGPUBalancerService
from backend.app.inference.cuda_optimization import CUDAOptimizationService
from backend.app.inference.flash_attention import FlashAttentionService
from backend.app.inference.kv_compression import KVCompressionService
from backend.app.inference.moe_routing import MoERoutingService
from backend.app.inference.pipeline_parallel import PipelineParallelService
from backend.app.inference.prefix_caching import PrefixCachingService
from backend.app.inference.quantized_inference import QuantizedInferenceService
from backend.app.inference.speculative_decoding import SpeculativeDecodingService
from backend.app.inference.tensor_parallel import TensorParallelService
from backend.app.inference.triton_kernels import TritonKernelsService
from backend.app.inference.async_inference_scheduler import InferenceRequest

logger = logging.getLogger(__name__)


class InferencePerformanceRegistry:
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, component: Any) -> None:
        cls._registry[name] = component
        logger.debug("Registered inference component: %s", name)

    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        return cls._registry.get(name)

    @classmethod
    def list_components(cls) -> List[str]:
        return list(cls._registry.keys())


__all__ = [
    "AsyncInferenceSchedulerService",
    "CPUGPUBalancerService",
    "CUDAOptimizationService",
    "DynamicBatchingService",
    "FlashAttentionService",
    "InferencePerformanceRegistry",
    "InferenceRequest",
    "KVCompressionService",
    "MoERoutingService",
    "PipelineParallelService",
    "PrefixCachingService",
    "Priority",
    "QuantizedInferenceService",
    "SpeculativeDecodingService",
    "TensorParallelService",
    "TritonKernelsService",
]
