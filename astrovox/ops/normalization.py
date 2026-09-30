"""Normalization operations.

LayerNorm and RMSNorm are the two normalizations used by essentially every
modern transformer, so they get first-class kernels with exact backward passes
including the gradient flowing back through the scale and shift parameters.
"""

from __future__ import annotations

import numpy as np

from astrovox.autograd.function import Function
from astrovox.tensor.tensor import Tensor


class LayerNorm(Function):
    """Layer normalization over the trailing ``normalized_shape`` dimensions.

    Args:
        x: input tensor.
        normalized_shape: shape of the trailing axes to normalize together.
        weight: optional per-channel scale.
        bias: optional per-channel shift.
        eps: numerical floor added to the variance.
    """

    name = "layer_norm"

    @staticmethod
    def forward(ctx, x, normalized_shape, weight, bias, eps: float):
        array = x.numpy()
        dims = tuple(normalized_shape)
        keep = array.shape[: array.ndim - len(dims)]
        grouped = array.reshape(keep + dims)

        mean = grouped.mean(axis=-1, keepdims=True)
        centered = grouped - mean
        variance = (centered**2).mean(axis=-1, keepdims=True)
        inv_std = 1.0 / np.sqrt(variance + eps)
        normalized = centered * inv_std

        out = normalized
        if weight is not None:
            out = out * weight.numpy().reshape((1,) * len(keep) + dims)
        if bias is not None:
            out = out + bias.numpy().reshape((1,) * len(keep) + dims)

        ctx.save(
            x=x,
            normalized=normalized,
            inv_std=inv_std,
            weight=weight,
            bias=bias,
            keep=keep,
            dims=dims,
            eps=eps,
        )
        result = Tensor.from_numpy(out.reshape(x.shape.dims), x.dtype, x.device)
        result.requires_grad_(x.requires_grad or (weight is not None and weight.requires_grad))
        return result

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.load("x")
        normalized = ctx.load("normalized")
        inv_std = ctx.load("inv_std")
        weight = ctx.load("weight")
        bias = ctx.load("bias")
        keep = ctx.load("keep")
        dims = ctx.load("dims")

        grad = grad_output.numpy().reshape(keep + dims)
        if weight is not None:
            grad = grad * weight.numpy().reshape((1,) * len(keep) + dims)

        grad_x = _layer_norm_backward(grad, normalized, inv_std).reshape(x.shape.dims)

        # Reduce over every axis except the feature axes to get parameter grads.
        feature_axes = tuple(range(len(keep), len(keep) + len(dims)))
        reduce_axes = tuple(i for i in range(grad.ndim) if i not in feature_axes)
        raw = grad_output.numpy().reshape(keep + dims)

        grad_weight = Tensor.from_numpy(raw.sum(axis=reduce_axes), weight.dtype) if weight is not None else None
        grad_bias = Tensor.from_numpy(raw.sum(axis=reduce_axes), bias.dtype) if bias is not None else None

        return Tensor.from_numpy(grad_x, x.dtype, x.device), None, grad_weight, grad_bias, None


def _layer_norm_backward(grad: np.ndarray, normalized: np.ndarray, inv_std: np.ndarray) -> np.ndarray:
    """Compute the LayerNorm input gradient.

    With ``x_hat = (x - mean) * inv_std``, the chain rule collapses to
    ``grad_x = inv_std * (g - mean(g) - x_hat * mean(g * x_hat))``.
    """
    mean_grad = grad.mean(axis=-1, keepdims=True)
    mean_grad_xhat = (grad * normalized).mean(axis=-1, keepdims=True)
    return inv_std * (grad - mean_grad - normalized * mean_grad_xhat)


class RMSNorm(Function):
    """Root-mean-square normalization: no mean subtraction, no bias.

    RMSNorm is cheaper than LayerNorm and works as well in practice for most
    transformer configurations, which is why modern LLMs prefer it.
    """

    name = "rms_norm"

    @staticmethod
    def forward(ctx, x, normalized_shape, weight, eps: float):
        array = x.numpy()
        dims = tuple(normalized_shape)
        keep = array.shape[: array.ndim - len(dims)]
        grouped = array.reshape(keep + dims)

        mean_square = (grouped**2).mean(axis=-1, keepdims=True)
        inv_rms = 1.0 / np.sqrt(mean_square + eps)
        normalized = grouped * inv_rms

        out = normalized
        if weight is not None:
            out = out * weight.numpy().reshape((1,) * len(keep) + dims)

        ctx.save(x=x, normalized=normalized, inv_rms=inv_rms, weight=weight, keep=keep, dims=dims)
        result = Tensor.from_numpy(out.reshape(x.shape.dims), x.dtype, x.device)
        result.requires_grad_(x.requires_grad or (weight is not None and weight.requires_grad))
        return result

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.load("x")
        normalized = ctx.load("normalized")
        inv_rms = ctx.load("inv_rms")
        weight = ctx.load("weight")
        keep = ctx.load("keep")
        dims = ctx.load("dims")

        grad = grad_output.numpy().reshape(keep + dims)
        if weight is not None:
            grad = grad * weight.numpy().reshape((1,) * len(keep) + dims)

        # inv_rms depends on x, so its contribution must be differentiated too:
        #   d/dx (x * inv_rms) = inv_rms * (g - x_hat * mean(g * x_hat))
        mean_grad_xhat = (grad * normalized).mean(axis=-1, keepdims=True)
        grad_x = (inv_rms * (grad - normalized * mean_grad_xhat)).reshape(x.shape.dims)

        feature_axes = tuple(range(len(keep), len(keep) + len(dims)))
        reduce_axes = tuple(i for i in range(grad.ndim) if i not in feature_axes)
        raw = grad_output.numpy().reshape(keep + dims)
        grad_weight = Tensor.from_numpy(raw.sum(axis=reduce_axes), weight.dtype) if weight is not None else None

        return Tensor.from_numpy(grad_x, x.dtype, x.device), None, grad_weight, None


def layer_norm(
    x: Tensor,
    normalized_shape: tuple[int, ...],
    weight: Tensor | None = None,
    bias: Tensor | None = None,
    eps: float = 1e-5,
) -> Tensor:
    """Layer-normalize ``x`` over its trailing dimensions."""
    return LayerNorm.apply(x, normalized_shape, weight, bias, eps)


def rms_norm(
    x: Tensor,
    normalized_shape: tuple[int, ...],
    weight: Tensor | None = None,
    eps: float = 1e-6,
) -> Tensor:
    """RMS-normalize ``x`` over its trailing dimensions."""
    return RMSNorm.apply(x, normalized_shape, weight, eps)


def group_norm(x: Tensor, num_groups: int, normalized_shape: tuple[int, ...], eps: float = 1e-5) -> Tensor:
    """Group normalization: LayerNorm applied independently per group.

    Useful for convolutional backbones, where LayerNorm over all channels
    discards the spatial grouping that BatchNorm exploited.
    """
    if num_groups <= 0:
        raise ValueError(f"num_groups must be positive, got {num_groups}")
    dims = tuple(normalized_shape)
    keep = x.shape.dims[: x.ndim - len(dims)]
    array = x.numpy().reshape(keep + dims)
    channels = array.shape[-2] if len(dims) > 1 else array.shape[-1]
    if channels % num_groups:
        raise ValueError(f"Channel count {channels} is not divisible by num_groups {num_groups}")

    grouped = array.reshape(keep + (num_groups, channels // num_groups) + dims[1:])
    mean = grouped.mean(axis=tuple(range(2, grouped.ndim)), keepdims=True)
    centered = grouped - mean
    variance = (centered**2).mean(axis=tuple(range(2, grouped.ndim)), keepdims=True)
    out = centered / np.sqrt(variance + eps)
    out = out.reshape(x.shape.dims)
    return Tensor.from_numpy(out, x.dtype, x.device).requires_grad_(x.requires_grad)
