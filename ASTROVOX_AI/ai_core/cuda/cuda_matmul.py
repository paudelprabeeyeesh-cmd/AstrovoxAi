import math
from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class CUDAMatMul:
    @staticmethod
    def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return torch.matmul(a, b)

    @staticmethod
    def batch_matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return torch.bmm(a, b)

    @staticmethod
    def outer_product(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return torch.outer(a, b)

    @staticmethod
    def hadamard(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return a * b

    @staticmethod
    def fused_matmul_add(a: torch.Tensor, b: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        return torch.addmm(c, a, b)

    @staticmethod
    def tiled_matmul(a: torch.Tensor, b: torch.Tensor, tile_size: int = 32) -> torch.Tensor:
        B, M, K = a.shape
        K2, N = b.shape[1], b.shape[2]
        out = torch.empty(B, M, N, device=a.device, dtype=a.dtype)
        for bi in range(0, B):
            for i in range(0, M, tile_size):
                for j in range(0, N, tile_size):
                    a_tile = a[bi, i:i + tile_size, :]
                    b_tile = b[bi, :, j:j + tile_size]
                    out[bi, i:i + tile_size, j:j + tile_size] = a_tile @ b_tile
        return out
