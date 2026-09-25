from typing import Optional, List, Tuple
import torch
import torch.nn as nn


class KVCacheCompressor:
    def __init__(self, compression_ratio: float = 0.5, method: str = 'mean'):
        self.compression_ratio = compression_ratio
        self.method = method

    def compress(self, k: torch.Tensor, v: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.method == 'mean':
            k_compressed = self._mean_pool(k)
            v_compressed = self._mean_pool(v)
        elif self.method == 'max':
            k_compressed = self._max_pool(k)
            v_compressed = self._max_pool(v)
        else:
            k_compressed, v_compressed = self._quantize(k, v)
        return k_compressed, v_compressed

    def decompress(self, k: torch.Tensor, v: torch.Tensor, original_shape: Tuple[int, ...]) -> Tuple[torch.Tensor, torch.Tensor]:
        k_expanded = k.unsqueeze(-2).repeat_interleave(original_shape[-2] // k.shape[-2], dim=-2)
        v_expanded = v.unsqueeze(-2).repeat_interleave(original_shape[-2] // v.shape[-2], dim=-2)
        return k_expanded, v_expanded

    def _mean_pool(self, x: torch.Tensor) -> torch.Tensor:
        B, H, T, D = x.shape
        pooled_T = max(1, int(T * self.compression_ratio))
        x_reshaped = x.view(B, H, pooled_T, T // pooled_T, D)
        return x_reshaped.mean(dim=3)

    def _max_pool(self, x: torch.Tensor) -> torch.Tensor:
        B, H, T, D = x.shape
        pooled_T = max(1, int(T * self.compression_ratio))
        x_reshaped = x.view(B, H, pooled_T, T // pooled_T, D)
        return x_reshaped.max(dim=3)[0]

    def _quantize(self, k: torch.Tensor, v: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        k_q = (k / (k.abs().max(dim=-1, keepdim=True)[0] + 1e-8) * 127).to(torch.int8)
        v_q = (v / (v.abs().max(dim=-1, keepdim=True)[0] + 1e-8) * 127).to(torch.int8)
        return k_q.float(), v_q.float()
