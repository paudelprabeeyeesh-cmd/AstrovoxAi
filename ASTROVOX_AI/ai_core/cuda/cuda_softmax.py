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
    def _softmax_kernel(
        x_ptr, y_ptr,
        M, N,
        stride_xm, stride_xn,
        stride_ym, stride_yn,
        BLOCK_N: tl.constexpr,
    ):
        row_idx = tl.program_id(0)
        cols = tl.arange(0, BLOCK_N)
        x_ptrs = x_ptr + row_idx * stride_xm + cols * stride_xn
        mask = cols < N
        x = tl.load(x_ptrs, mask=mask, other=float('-inf'))
        row_max = tl.max(x, axis=0)
        x_shifted = x - row_max
        x_exp = tl.exp(x_shifted)
        row_sum = tl.sum(x_exp, axis=0)
        y = x_exp / row_sum
        y_ptrs = y_ptr + row_idx * stride_ym + cols * stride_yn
        tl.store(y_ptrs, y, mask=mask)

    @triton.jit
    def _masked_softmax_kernel(
        x_ptr, mask_ptr, y_ptr,
        M, N,
        stride_xm, stride_xn,
        stride_maskm, stride_maskn,
        stride_ym, stride_yn,
        BLOCK_N: tl.constexpr,
    ):
        row_idx = tl.program_id(0)
        cols = tl.arange(0, BLOCK_N)
        x_ptrs = x_ptr + row_idx * stride_xm + cols * stride_xn
        mask_ptrs = mask_ptr + row_idx * stride_maskm + cols * stride_maskn
        mask = cols < N
        x = tl.load(x_ptrs, mask=mask, other=float('-inf'))
        m = tl.load(mask_ptrs, mask=mask, other=0)
        x = tl.where(m == 0, float('-inf'), x)
        row_max = tl.max(x, axis=0)
        x_shifted = x - row_max
        x_exp = tl.exp(x_shifted)
        row_sum = tl.sum(x_exp, axis=0)
        y = x_exp / row_sum
        y_ptrs = y_ptr + row_idx * stride_ym + cols * stride_yn
        tl.store(y_ptrs, y, mask=mask)

    def softmax_triton(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
        if dim != -1:
            x = x.transpose(dim, -1)
        M, N = x.shape
        y = torch.empty_like(x)
        BLOCK_N = triton.next_power_of_2(N)
        grid = (M,)
        _softmax_kernel[grid](
            x, y,
            M, N,
            x.stride(0), x.stride(1),
            y.stride(0), y.stride(1),
            BLOCK_N=BLOCK_N,
        )
        if dim != -1:
            y = y.transpose(-1, dim)
        return y

    def masked_softmax_triton(x: torch.Tensor, mask: torch.Tensor, dim: int = -1) -> torch.Tensor:
        if dim != -1:
            x = x.transpose(dim, -1)
            mask = mask.transpose(dim, -1)
        M, N = x.shape
        y = torch.empty_like(x)
        BLOCK_N = triton.next_power_of_2(N)
        grid = (M,)
        _masked_softmax_kernel[grid](
            x, mask, y,
            M, N,
            x.stride(0), x.stride(1),
            mask.stride(0), mask.stride(1),
            y.stride(0), y.stride(1),
            BLOCK_N=BLOCK_N,
        )
        if dim != -1:
            y = y.transpose(-1, dim)
        return y


class CUDASoftmax(nn.Module):
    def __init__(self, dim: int = -1, use_fast_math: bool = True, use_triton: bool = True):
        super().__init__()
        self.dim = dim
        self.use_fast_math = use_fast_math
        self.use_triton = use_triton and TRITON_AVAILABLE

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_triton:
            return softmax_triton(x, self.dim)
        if self.use_fast_math:
            return torch.softmax(x, dim=self.dim)
        x_max, _ = x.max(dim=self.dim, keepdim=True)
        x_exp = torch.exp(x - x_max)
        return x_exp / x_exp.sum(dim=self.dim, keepdim=True)


class CUDASoftmaxWithMask(nn.Module):
    def __init__(self, dim: int = -1, use_triton: bool = True):
        super().__init__()
        self.dim = dim
        self.use_triton = use_triton and TRITON_AVAILABLE

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        if mask is not None:
            if self.use_triton:
                return masked_softmax_triton(x, mask, self.dim)
            x = x.masked_fill(mask == 0, float('-inf'))
        if self.use_triton:
            return softmax_triton(x, self.dim)
        return torch.softmax(x, dim=self.dim)


class FlashSoftmax:
    @staticmethod
    def forward(x: torch.Tensor, dim: int = -1) -> torch.Tensor:
        if TRITON_AVAILABLE:
            return softmax_triton(x, dim)
        return torch.softmax(x, dim=dim)
