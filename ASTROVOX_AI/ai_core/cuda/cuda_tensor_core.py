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
    def _tensor_core_matmul_kernel(
        a_ptr, b_ptr, c_ptr,
        M, N, K,
        stride_am, stride_ak,
        stride_bk, stride_bn,
        stride_cm, stride_cn,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
        SPLIT_K: tl.constexpr = 1,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        pid_k = tl.program_id(2)
        rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        rk = pid_k * BLOCK_K + tl.arange(0, BLOCK_K)
        acc = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for k in range(0, K, BLOCK_K * SPLIT_K):
            k_remaining = min(BLOCK_K, K - k - pid_k * BLOCK_K)
            if k_remaining <= 0:
                continue
            a_mask = (rm[:, None] < M) & (rk[None, :] < K)
            b_mask = (rn[:, None] < N) & (rk[None, :] < K)
            a = tl.load(a_ptr + rm[:, None] * stride_am + rk[None, :] * stride_ak, mask=a_mask, other=0.0)
            b = tl.load(b_ptr + rk[:, None] * stride_bk + rn[None, :] * stride_bn, mask=b_mask, other=0.0)
            acc += tl.dot(a, b)
        c_mask = (rm[:, None] < M) & (rn[None, :] < N)
        tl.store(c_ptr + rm[:, None] * stride_cm + rn[None, :] * stride_cn, acc, mask=c_mask)

    def tensor_core_matmul_triton(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        M, K = a.shape
        K2, N = b.shape
        assert K == K2
        c = torch.empty(M, N, device=a.device, dtype=a.dtype)
        BLOCK_M, BLOCK_N, BLOCK_K = 16, 16, 32
        SPLIT_K = 1
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N), SPLIT_K)
        _tensor_core_matmul_kernel[grid](
            a, b, c,
            M, N, K,
            a.stride(0), a.stride(1),
            b.stride(0), b.stride(1),
            c.stride(0), c.stride(1),
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
            SPLIT_K=SPLIT_K,
        )
        return c


class CUDATensorCoreMatMul(nn.Module):
    def __init__(self, use_triton: bool = True):
        super().__init__()
        self.use_triton = use_triton and TRITON_AVAILABLE

    def forward(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        if self.use_triton:
            return tensor_core_matmul_triton(a, b)
        if hasattr(torch, 'amp') and a.dtype == torch.float16:
            with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                return torch.matmul(a, b)
        return torch.matmul(a, b)


class CUDATensorCoreAttention(nn.Module):
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
        if self.use_triton:
            attn = tensor_core_matmul_triton(q.reshape(-1, T, self.head_dim), k.reshape(-1, T, self.head_dim).transpose(-2, -1))
            attn = attn.view(B, self.num_heads, T, T) * self.scale
        else:
            attn = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        attn = attn.softmax(dim=-1)
        if self.use_triton:
            out = tensor_core_matmul_triton(attn.reshape(-1, T, T), v.reshape(-1, T, self.head_dim))
            out = out.view(B, self.num_heads, T, self.head_dim)
        else:
            out = torch.matmul(attn, v)
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)


class CUDATensorCoreMLP(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, use_triton: bool = True):
        super().__init__()
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size
        self.use_triton = use_triton and TRITON_AVAILABLE
        self.gate_proj = nn.Linear(hidden_size, intermediate_size)
        self.up_proj = nn.Linear(hidden_size, intermediate_size)
        self.down_proj = nn.Linear(intermediate_size, hidden_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gate = self.gate_proj(x)
        up = self.up_proj(x)
        hidden = F.silu(gate) * up
        if self.use_triton:
            return tensor_core_matmul_triton(hidden, self.down_proj.weight.t())
        return self.down_proj(hidden)
