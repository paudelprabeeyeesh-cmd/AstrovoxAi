from typing import Optional
import torch
import torch.nn as nn

try:
    import triton
    import triton.language as tl
    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False


if TRITON_AVAILABLE:
    @triton.jit
    def _warp_reduce_sum(x_ptr, block_size: tl.constexpr):
        mask = tl.arange(0, block_size) < block_size
        x = tl.load(x_ptr, mask=mask, other=0.0)
        x = tl.sum(x, axis=0)
        return x

    @triton.jit
    def _warp_softmax_kernel(
        x_ptr, y_ptr,
        M, N,
        x_stride_m, x_stride_n,
        y_stride_m, y_stride_n,
        BLOCK_N: tl.constexpr,
        NUM_WARPS: tl.constexpr,
    ):
        pid = tl.program_id(0)
        row_start = pid * BLOCK_N
        row_idx = row_start + tl.arange(0, BLOCK_N)
        cols = tl.arange(0, NUM_WARPS * 32)
        x_ptrs = x_ptr + row_idx[:, None] * x_stride_m + cols[None, :] * x_stride_n
        mask = (row_idx[:, None] < M) & (cols[None, :] < N)
        x = tl.load(x_ptrs, mask=mask, other=float('-inf'))
        row_max = tl.max(x, axis=1)
        x_shifted = x - row_max[:, None]
        x_exp = tl.exp(x_shifted)
        row_sum = tl.sum(x_exp, axis=1)
        y = x_exp / row_sum[:, None]
        y_ptrs = y_ptr + row_idx[:, None] * y_stride_m + cols[None, :] * y_stride_n
        tl.store(y_ptrs, y, mask=mask)

    def warp_optimized_softmax_triton(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
        if dim != -1:
            x = x.transpose(dim, -1)
        M, N = x.shape
        y = torch.empty_like(x)
        BLOCK_N = triton.next_power_of_2(N)
        NUM_WARPS = max(1, BLOCK_N // 32)
        grid = (M,)
        _warp_softmax_kernel[grid](
            x, y,
            M, N,
            x.stride(0), x.stride(1),
            y.stride(0), y.stride(1),
            BLOCK_N=BLOCK_N,
            NUM_WARPS=NUM_WARPS,
        )
        if dim != -1:
            y = y.transpose(-1, dim)
        return y


class WarpOptimizedSoftmax(nn.Module):
    def __init__(self, dim: int = -1, use_triton: bool = True):
        super().__init__()
        self.dim = dim
        self.use_triton = use_triton and TRITON_AVAILABLE

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_triton:
            return warp_optimized_softmax_triton(x, self.dim)
        return torch.softmax(x, dim=self.dim)


class WarpOptimizedLayerNorm(nn.Module):
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


class WarpOptimizedAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, use_triton: bool = True):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
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
        attn = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        if self.use_triton and TRITON_AVAILABLE:
            attn = warp_optimized_softmax_triton(attn, dim=-1)
        else:
            attn = attn.softmax(dim=-1)
        out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
