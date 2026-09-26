from typing import Optional, List
import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import logging

logger = logging.getLogger(__name__)

try:
    import triton
    import triton.language as tl
    TRITON_AVAILABLE = True
except ImportError:
    TRITON_AVAILABLE = False


if TRITON_AVAILABLE:
    @triton.jit
    def _flash_attention_kernel(
        q_ptr, k_ptr, v_ptr, o_ptr,
        M, N, D,
        stride_qm, stride_qd,
        stride_kn, stride_kd,
        stride_vn, stride_vd,
        stride_om, stride_od,
        scale,
        causal: tl.constexpr,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_D: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        start_m = pid_m * BLOCK_M
        rm = start_m + tl.arange(0, BLOCK_M)
        rd = tl.arange(0, BLOCK_D)
        acc = tl.zeros((BLOCK_M, BLOCK_D), dtype=tl.float32)
        l_i = tl.zeros((BLOCK_M,), dtype=tl.float32) - float('inf')
        m_i = tl.zeros((BLOCK_M,), dtype=tl.float32) - float('inf')
        for start_n in range(0, N, BLOCK_N):
            end_n = min(start_n + BLOCK_N, N)
            rn = start_n + tl.arange(0, BLOCK_N)
            q_mask = (rm[:, None] < M) & (rd[None, :] < D)
            k_mask = (rn[:, None] < N) & (rd[None, :] < D)
            q = tl.load(q_ptr + rm[:, None] * stride_qm + rd[None, :] * stride_qd, mask=q_mask, other=0.0)
            k = tl.load(k_ptr + rn[:, None] * stride_kn + rd[None, :] * stride_kd, mask=k_mask, other=0.0)
            qk = tl.dot(q, tl.trans(k))
            if causal:
                causal_mask = (rm[:, None] >= rn[None, :])
                qk = tl.where(causal_mask, qk, float('-inf'))
            qk = qk * scale
            m_ij = tl.max(qk, axis=1)
            p_ij = tl.exp(qk - m_ij[:, None])
            l_ij = tl.sum(p_ij, axis=1)
            v_mask = (rn[:, None] < N) & (rd[None, :] < D)
            v = tl.load(v_ptr + rn[:, None] * stride_vn + rd[None, :] * stride_vd, mask=v_mask, other=0.0)
            pv = tl.dot(p_ij.to(tl.float32), v)
            m_new = tl.maximum(m_i, m_ij)
            alpha = tl.exp(m_i - m_new)
            l_new = alpha * l_i + tl.exp(m_ij - m_new)
            acc = acc * alpha[:, None] + pv
            l_i = l_new
            m_i = m_new
        acc = acc / l_i[:, None]
        o_mask = (rm[:, None] < M) & (rd[None, :] < D)
        tl.store(o_ptr + rm[:, None] * stride_om + rd[None, :] * stride_od, acc, mask=o_mask)

    def flash_attention_triton(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, causal: bool = True) -> torch.Tensor:
        B, H, M, D = q.shape
        N = k.shape[2]
        scale = D ** -0.5
        o = torch.empty_like(q)
        BLOCK_M, BLOCK_N, BLOCK_D = 16, 16, min(triton.next_power_of_2(D), 64)
        grid = (triton.cdiv(M, BLOCK_M),)
        _flash_attention_kernel[grid](
            q, k, v, o,
            M, N, D,
            q.stride(2), q.stride(3),
            k.stride(2), k.stride(3),
            v.stride(2), v.stride(3),
            o.stride(2), o.stride(3),
            scale, causal,
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_D=BLOCK_D,
        )
        return o


class CUDAAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, dropout: float = 0.0, use_flash: bool = False, use_triton: bool = True):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, hidden_size)
        self.v_proj = nn.Linear(hidden_size, hidden_size)
        self.out_proj = nn.Linear(hidden_size, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.use_flash = use_flash
        self.use_triton = use_triton and TRITON_AVAILABLE

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        if self.use_flash:
            try:
                from flash_attn import flash_attn_func
                out = flash_attn_func(q, k, v, dropout_p=self.dropout.p, causal=True)
                return self.out_proj(out.view(B, T, C))
            except ImportError:
                logger.warning("flash_attn not installed, falling back to SDPA")
                attn = F.scaled_dot_product_attention(q, k, v, attn_mask=mask, dropout_p=self.dropout.p if self.training else 0.0)
                return self.out_proj(attn.transpose(1, 2).contiguous().view(B, T, C))
        if self.use_triton and TRITON_AVAILABLE:
            out = flash_attention_triton(q, k, v, causal=True)
        else:
            attn = (q @ k.transpose(-2, -1)) * self.scale
            if mask is not None:
                attn = attn.masked_fill(mask == 0, float('-inf'))
            attn = attn.softmax(dim=-1)
            attn = self.dropout(attn)
            out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)


class CUDAMultiQueryAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, num_kv_heads: int, dropout: float = 0.0):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.num_kv_heads = num_kv_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.q_proj = nn.Linear(hidden_size, hidden_size)
        self.k_proj = nn.Linear(hidden_size, num_kv_heads * self.head_dim)
        self.v_proj = nn.Linear(hidden_size, num_kv_heads * self.head_dim)
        self.out_proj = nn.Linear(hidden_size, hidden_size)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, C = x.shape
        q = self.q_proj(x).view(B, T, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.num_kv_heads, self.head_dim).transpose(1, 2)
        k = k.repeat_interleave(self.num_heads // self.num_kv_heads, dim=1)
        v = v.repeat_interleave(self.num_heads // self.num_kv_heads, dim=1)
        attn = (q @ k.transpose(-2, -1)) * self.scale
        if mask is not None:
            attn = attn.masked_fill(mask == 0, float('-inf'))
        attn = attn.softmax(dim=-1)
        attn = self.dropout(attn)
        out = attn @ v
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)


class CUDAFlashAttention(nn.Module):
    def __init__(self, hidden_size: int, num_heads: int, block_size_m: int = 64, block_size_n: int = 64, use_triton: bool = True):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        self.scale = self.head_dim ** -0.5
        self.block_size_m = block_size_m
        self.block_size_n = block_size_n
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
            out = flash_attention_triton(q, k, v, causal=True)
        else:
            out = torch.zeros_like(q)
            for start_m in range(0, T, self.block_size_m):
                end_m = min(start_m + self.block_size_m, T)
                q_block = q[:, :, start_m:end_m, :]
                acc = torch.zeros(B, self.num_heads, end_m - start_m, self.head_dim, device=q.device, dtype=q.dtype)
                for start_n in range(0, T, self.block_size_n):
                    end_n = min(start_n + self.block_size_n, T)
                    k_block = k[:, :, start_n:end_n, :]
                    v_block = v[:, :, start_n:end_n, :]
                    attn_weights = torch.matmul(q_block, k_block.transpose(-2, -1)) * self.scale
                    if mask is not None:
                        mask_block = mask[..., start_m:end_m, start_n:end_n]
                        attn_weights = attn_weights.masked_fill(mask_block == 0, float('-inf'))
                    attn_weights = torch.softmax(attn_weights, dim=-1)
                    acc = acc + torch.matmul(attn_weights, v_block)
                out[:, :, start_m:end_m, :] = acc
        out = out.transpose(1, 2).contiguous().view(B, T, C)
        return self.out_proj(out)
