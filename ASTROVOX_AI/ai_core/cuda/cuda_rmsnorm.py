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
    def _rms_norm_kernel(
        x_ptr, y_ptr, weight_ptr,
        M, N, eps,
        x_stride_m, x_stride_n,
        y_stride_m, y_stride_n,
        BLOCK_N: tl.constexpr,
    ):
        row_idx = tl.program_id(0)
        cols = tl.arange(0, BLOCK_N)
        mask = cols < N
        x_ptrs = x_ptr + row_idx * x_stride_m + cols * x_stride_n
        x = tl.load(x_ptrs, mask=mask, other=0.0)
        variance = tl.sum(x * x, axis=0) / N
        rstd = tl.rsqrt(variance + eps)
        y = x * rstd
        if weight_ptr is not None:
            w = tl.load(weight_ptr + cols, mask=mask, other=1.0)
            y = y * w
        y_ptrs = y_ptr + row_idx * y_stride_m + cols * y_stride_n
        tl.store(y_ptrs, y, mask=mask)

    def rms_norm_triton(x: torch.Tensor, weight: Optional[torch.Tensor], eps: float = 1e-6) -> torch.Tensor:
        M, N = x.shape
        y = torch.empty_like(x)
        BLOCK_N = triton.next_power_of_2(N)
        grid = (M,)
        _rms_norm_kernel[grid](
            x, y, weight,
            M, N, eps,
            x.stride(0), x.stride(1),
            y.stride(0), y.stride(1),
            BLOCK_N=BLOCK_N,
        )
        return y


class CUDARMSNorm(nn.Module):
    def __init__(self, hidden_size: int, eps: float = 1e-6, use_triton: bool = True):
        super().__init__()
        self.hidden_size = hidden_size
        self.eps = eps
        self.use_triton = use_triton and TRITON_AVAILABLE
        self.weight = nn.Parameter(torch.ones(hidden_size))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_triton:
            return rms_norm_triton(x, self.weight, self.eps)
        variance = x.pow(2).mean(-1, keepdim=True)
        x = x * torch.rsqrt(variance + self.eps)
        return self.weight * x


class CUDARMSNormImpl:
    @staticmethod
    def forward(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        if TRITON_AVAILABLE:
            return rms_norm_triton(x, weight, eps)
        variance = x.pow(2).mean(-1, keepdim=True)
        x = x * torch.rsqrt(variance + eps)
        return weight * x
