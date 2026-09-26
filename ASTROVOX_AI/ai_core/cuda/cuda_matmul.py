from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    import triton
    import triton.language as tl
    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False


if TRITON_AVAILABLE:
    @triton.jit
    def _matmul_kernel(
        a_ptr, b_ptr, c_ptr,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        rk = tl.arange(0, BLOCK_K)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for k in range(0, K, BLOCK_K):
            k_remaining = min(BLOCK_K, K - k)
            a_mask = (rm[:, None] < M) & (rk[None, :] < K)
            b_mask = (rn[:, None] < N) & (rk[None, :] < K)
            a = tl.load(a_ptr + rm[:, None] * stride_am + (k + rk[None, :]) * stride_ak, mask=a_mask, other=0.0)
            b = tl.load(b_ptr + (k + rk[:, None]) * stride_bk + rn[None, :] * stride_bn, mask=b_mask, other=0.0)
            acc += tl.dot(a, b)
        c_mask = (rm[:, None] < M) & (rn[None, :] < N)
        tl.store(c_ptr + rm[:, None] * stride_cm + rn[None, :] * stride_cn, acc, mask=c_mask)

    def matmul_triton(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        M, K = a.shape
        K2, N = b.shape
        assert K == K2
        c = torch.empty(M, N, device=a.device, dtype=a.dtype)
        BLOCK_M, BLOCK_N, BLOCK_K = 16, 16, 32
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        _matmul_kernel[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1),
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        )
        return c


class CUDAMatMul:
    @staticmethod
    def matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if TRITON_AVAILABLE:
            return matmul_triton(a, b)
        return torch.matmul(a, b)

    @staticmethod
    def batch_matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        B, M, K = a.shape
        K2, N = b.shape[2], b.shape[2]
        if TRITON_AVAILABLE:
            out = torch.empty(B, M, N, device=a.device, dtype=a.dtype)
            for bi in range(B):
                out[bi] = matmul_triton(a[bi], b[bi])
            return out
        return torch.bmm(a, b)

    @staticmethod
    def outer_product(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if TRITON_AVAILABLE:
            return matmul_triton(a.unsqueeze(1), b.unsqueeze(0)).squeeze()
        return torch.outer(a, b)

    @staticmethod
    def hadamard(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return a * b

    @staticmethod
    def fused_matmul_add(a: torch.Tensor, b: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        if TRITON_AVAILABLE:
            ab = matmul_triton(a, b)
            return ab + c
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
                    if TRITON_AVAILABLE:
                        out[bi, i:i + tile_size, j:j + tile_size] = matmul_triton(a_tile, b_tile)
                    else:
                        out[bi, i:i + tile_size, j:j + tile_size] = a_tile @ b_tile
        return out

    @staticmethod
    def tensor_core_matmul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if a.dtype in (torch.float16, torch.bfloat16) and TRITON_AVAILABLE:
            return matmul_triton(a, b)
        if hasattr(torch, 'amp'):
            with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                return torch.matmul(a, b)
        return torch.matmul(a, b)


class CUDAMatMulModule(nn.Module):
    def __init__(self, use_triton: bool = True):
        super().__init__()
        self.use_triton = use_triton and TRITON_AVAILABLE

    def forward(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if self.use_triton:
            return matmul_triton(a, b)
        return torch.matmul(a, b)
