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


class QuantizedLinear(nn.Module):
    def __init__(self, in_features: int, out_features: int, weight_bits: int = 8, use_triton: bool = True):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight_bits = weight_bits
        self.use_triton = use_triton and TRITON_AVAILABLE
        self.weight = nn.Parameter(torch.randn(out_features, in_features))
        self.scale = nn.Parameter(torch.ones(out_features))
        self.zero_point = nn.Parameter(torch.zeros(out_features))

    def quantize_weight(self) -> torch.Tensor:
        w = self.weight.detach()
        qmin = -(2 ** (self.weight_bits - 1))
        qmax = 2 ** (self.weight_bits - 1) - 1
        scale = (w.max(dim=1)[0] - w.min(dim=1)[0]) / (qmax - qmin)
        scale = torch.clamp(scale, min=1e-8)
        zero_point = torch.clamp(-w.min(dim=1)[0] / scale, qmin, qmax).round()
        q_weight = ((w / scale.unsqueeze(1)) + zero_point.unsqueeze(1)).round().clamp(qmin, qmax)
        return q_weight, scale, zero_point

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        q_weight, scale, zero_point = self.quantize_weight()
        if self.use_triton and TRITON_AVAILABLE:
            return quantized_matmul_triton(x, q_weight, scale, zero_point, self.weight_bits)
        dequant_weight = (q_weight.float() - zero_point.unsqueeze(1)) * scale.unsqueeze(1)
        return F.linear(x, dequant_weight)


if TRITON_AVAILABLE:
    @triton.jit
    def _quantized_matmul_kernel(
        x_ptr, qw_ptr, y_ptr,
        scale_ptr, zp_ptr,
        M, N, K, q_bits,
        x_stride_m, x_stride_k,
        qw_stride_n, qw_stride_k,
        y_stride_m, y_stride_n,
        BLOCK_M: tl.constexpr, BLOCK_N: tl.constexpr, BLOCK_K: tl.constexpr,
    ):
        pid_m = tl.program_id(0)
        pid_n = tl.program_id(1)
        rm = pid_m * BLOCK_M + tl.arange(0, BLOCK_M)
        rn = pid_n * BLOCK_N + tl.arange(0, BLOCK_N)
        accumulator = tl.zeros((BLOCK_M, BLOCK_N), dtype=tl.float32)
        for k in range(0, K, BLOCK_K):
            rk = k + tl.arange(0, BLOCK_K)
            x_mask = (rm[:, None] < M) & (rk[None, :] < K)
            qw_mask = (rn[:, None] < N) & (rk[None, :] < K)
            x = tl.load(x_ptr + rm[:, None] * x_stride_m + rk[None, :] * x_stride_k, mask=x_mask, other=0.0)
            qw = tl.load(qw_ptr + rn[:, None] * qw_stride_n + rk[None, :] * qw_stride_k, mask=qw_mask, other=0.0).to(tl.float32)
            accumulator += tl.dot(x, qw)
        acc_mask = (rm[:, None] < M) & (rn[None, :] < N)
        scale = tl.load(scale_ptr + rn, mask=rn < N, other=1.0)
        zp = tl.load(zp_ptr + rn, mask=rn < N, other=0.0)
        accumulator = (accumulator - tl.sum(zp[None, :] * tl.sum(qw, axis=0), axis=1, keepdims=True)) * scale[None, :]
        tl.store(y_ptr + rm[:, None] * y_stride_m + rn[None, :] * y_stride_n, accumulator, mask=acc_mask)

    def quantized_matmul_triton(x: torch.Tensor, q_weight: torch.Tensor, scale: torch.Tensor, zero_point: torch.Tensor, q_bits: int = 8) -> torch.Tensor:
        M, K = x.shape
        N = q_weight.shape[0]
        y = torch.empty(M, N, device=x.device, dtype=x.dtype)
        BLOCK_M, BLOCK_N, BLOCK_K = 16, 16, 32
        grid = (triton.cdiv(M, BLOCK_M), triton.cdiv(N, BLOCK_N))
        _quantized_matmul_kernel[grid](
            x, q_weight, y, scale, zero_point,
            M, N, K, q_bits,
            x.stride(0), x.stride(1),
            q_weight.stride(0), q_weight.stride(1),
            y.stride(0), y.stride(1),
            BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_K=BLOCK_K,
        )
        return y


class CUDAAWQuantizedLinear(nn.Module):
    def __init__(self, in_features: int, out_features: int, group_size: int = 128):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.group_size = group_size
        self.num_groups = in_features // group_size
        self.q_weight = nn.Parameter(torch.zeros(out_features, in_features, dtype=torch.int8))
        self.scales = nn.Parameter(torch.zeros(out_features, self.num_groups, dtype=torch.float16))
        self.zero_points = nn.Parameter(torch.zeros(out_features, self.num_groups, dtype=torch.int8))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return awq_quantized_matmul(x, self.q_weight, self.scales, self.zero_points, self.group_size)


def awq_quantized_matmul(x: torch.Tensor, q_weight: torch.Tensor, scales: torch.Tensor, zero_points: torch.Tensor, group_size: int = 128) -> torch.Tensor:
    B, in_dim = x.shape
    out_dim = q_weight.shape[0]
    num_groups = in_dim // group_size
    x_reshaped = x.view(B, num_groups, group_size).float()
    dequant = ((q_weight.view(out_dim, num_groups, group_size).float() - zero_points.unsqueeze(2).float()) * scales.unsqueeze(2)).reshape(out_dim, in_dim)
    return x_reshaped @ dequant.t()


class CUDAGPTQQuantizedLinear(nn.Module):
    def __init__(self, in_features: int, out_features: int, bits: int = 4, group_size: int = 128):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.bits = bits
        self.group_size = group_size
        self.qweight = nn.Parameter(torch.zeros(out_features // 2, in_features, dtype=torch.int32))
        self.scales = nn.Parameter(torch.zeros(out_features, in_features // group_size, dtype=torch.float16))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return gptq_quantized_matmul(x, self.qweight, self.scales, self.bits, self.group_size)


def gptq_quantized_matmul(x: torch.Tensor, qweight: torch.Tensor, scales: torch.Tensor, bits: int = 4, group_size: int = 128) -> torch.Tensor:
    B, in_dim = x.shape
    out_dim = qweight.shape[0] * 2
    num_groups = in_dim // group_size
    x_reshaped = x.view(B, num_groups, group_size)
    w = qweight.view(out_dim, num_groups, group_size // 2)
    dequant = w.to(torch.float32).unsqueeze(3).repeat(1, 1, 1, 2).reshape(out_dim, in_dim) * scales.t().unsqueeze(2).repeat(1, 1, group_size).reshape(out_dim, in_dim)
    return x_reshaped @ dequant.t()
