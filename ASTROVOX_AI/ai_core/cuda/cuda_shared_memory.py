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
    def _shared_memory_matmul_kernel(
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

    def shared_memory_matmul_triton(a: torch.Tensor, b: torch.Tensor, tile_m: int = 64, tile_n: int = 64, tile_k: int = 32) -> torch.Tensor:
        M, K = a.shape
        K2, N = b.shape
        assert K == K2
        c = torch.empty(M, N, device=a.device, dtype=a.dtype)
        grid = (triton.cdiv(M, tile_m), triton.cdiv(N, tile_n))
        _shared_memory_matmul_kernel[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1),
            BLOCK_M=tile_m, BLOCK_N=tile_n, BLOCK_K=tile_k,
        )
        return c


class SharedMemoryMatMul(nn.Module):
    def __init__(self, tile_m: int = 64, tile_n: int = 64, tile_k: int = 32, use_triton: bool = True):
        super().__init__()
        self.tile_m = tile_m
        self.tile_n = tile_n
        self.tile_k = tile_k
        self.use_triton = use_triton and TRITON_AVAILABLE

    def forward(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if self.use_triton:
            return shared_memory_matmul_triton(a, b, self.tile_m, self.tile_n, self.tile_k)
        return torch.matmul(a, b)


class SharedMemorySoftmax(nn.Module):
    def __init__(self, dim: int = -1, use_triton: bool = True):
        super().__init__()
        self.dim = dim
        self.use_triton = use_triton and TRITON_AVAILABLE

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_triton and TRITON_AVAILABLE:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_warp_optimization import warp_optimized_softmax_triton
                return warp_optimized_softmax_triton(x, self.dim)
            except ImportError:
                pass
        return torch.softmax(x, dim=self.dim)


class SharedMemoryLayerNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float = 1e-6, use_triton: bool = True):
        super().__init__()
        self.hidden_size = hidden_size
        self.eps = eps
        self.use_triton = use_triton and TRITON_AVAILABLE
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.bias = nn.Parameter(torch.zeros(hidden_size))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_triton and TRITON_AVAILABLE:
            try:
                from ASTROVOX_AI.ai_core.cuda.cuda_layernorm import layer_norm_triton
                return layer_norm_triton(x, self.weight, self.bias, self.eps)
            except ImportError:
                pass
        return torch.nn.functional.layer_norm(x, self.hidden_size, self.weight, self.bias, self.eps)


class SharedMemoryAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, tile_m: int = 64, tile_n: int = 64, use_triton: bool = True):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.tile_m = tile_m
        self.tile_n = tile_n
        self.use_triton = use_triton and TRITON_AVAILABLE
        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.out_proj = nn.Linear(hidden_size, hidden_size)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        if self.use_triton and TRITON_AVAILABLE:
            out = torch.zeros_like(q)
            for start_m in range(0, T, self.tile_m):
                end_m = min(start_m + self.tile_m, T)
                q_block = q[:, :, start_m:end_m, :]
                acc = torch.zeros(B, self.num_heads, end_m - start_m, self.head_dim, device=q.device, dtype=q.dtype)
                for start_n in range(0, T, self.tile_n):
                    end_n = min(start_n + self.tile_n, T)
                    k_block = k[:, :, start_n:end_n, :]
                    v_block = v[:, :, start_n:end_n, :]
                    attn_weights = torch.matmul(q_block, k_block.transpose(-2, -1)) * self.scale
                    if mask is not None:
                        mask_block = mask[..., start_m:end_m, start_n:end_n]
                        attn_weights = attn_weights.masked_fill(mask_block == 0, float('-inf'))
                    attn_weights = torch.softmax(attn_weights, dim=-1)
                    acc = acc + torch.matmul(attn_weights, v_block)
                out[:, :, start_m:end_m, :] = acc
        else:
            attn = torch.matmul(q, k.transpose(-2, -1)) * self.scale
            if mask is not None:
                attn = attn.masked_fill(mask == 0, float('-inf'))
            attn = attn.softmax(dim=-1)
            out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
