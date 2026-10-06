"""Elementwise and matrix arithmetic.

Every op routes through :class:`~astrovox.autograd.function.Function` so the
compiler can see a uniform node type and the engine can differentiate all of
them the same way.
"""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

from astrovox.autograd.function import Function
from astrovox.tensor.broadcast import unbroadcast
from astrovox.tensor.dtype import DEFAULT, DType, resolve
from astrovox.tensor.shape import Shape, broadcast_shapes
from astrovox.tensor.tensor import Tensor


def _as_tensor(value: Tensor | float | int, like: Tensor | None = None) -> Tensor:
    """Convert a Python scalar into a tensor, matching ``like``'s dtype."""
    if isinstance(value, Tensor):
        return value
    dtype = resolve(DEFAULT) if like is None or not like.dtype.is_floating else like.dtype
    return Tensor.from_numpy(np.array(value, dtype=dtype.np_dtype), dtype)


def _result_dtype(a: Tensor, b: Tensor | float | int) -> DType:
    """Return the promoted dtype for a binary operation."""
    if isinstance(b, Tensor):
        return a.dtype.promote(b.dtype)
    return a.dtype


class Add(Function):
    """Elementwise addition with broadcasting."""

    name = "add"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        left = a if isinstance(a, Tensor) else _as_tensor(a)
        right = b if isinstance(b, Tensor) else _as_tensor(b, left)
        dtype = left.dtype.promote(right.dtype)
        out = Tensor.from_numpy(
            np.add(left.numpy().astype(dtype.np_dtype, copy=False), right.numpy().astype(dtype.np_dtype, copy=False)),
            dtype,
            left.device,
        )
        return out 

def split(tensor: Tensor, split_size: int, dim: int = 0) -> list[Tensor]:
    """Split a tensor into chunks along dimension dim.
    
    Args:
        tensor: The tensor to split
        split_size: Size of each chunk
        dim: Dimension along which to split
    
    Returns:
        List of tensors resulting from the split
    """
    
    dim = _normalize_axis(dim, tensor.ndim)
    shape = tensor.shape
    dim_size = shape.dims[dim]
    
    # Calculate number of splits
    num_splits = (dim_size + split_size - 1) // split_size
    
    result = []
    for i in range(num_splits):
        start = i * split_size
        end = min((i + 1) * split_size, dim_size)
        
        # Create a slice key
        key = [slice(None)] * tensor.ndim
        key[dim] = slice(start, end)
        
        # Get the split tensor
        split_tensor = tensor[tuple(key)]
        result.append(split_tensor)
    
    return result


def chunk(tensor: Tensor, chunks: int, dim: int = 0) -> list[Tensor]:
    """Split a tensor into roughly equal chunks along dimension dim.
    
    Args:
        tensor: The tensor to chunk
        chunks: Number of chunks
        dim: Dimension along which to chunk
    
    Returns:
        List of tensors resulting from the chunk
    """
    
    dim = _normalize_axis(dim, tensor.ndim)
    shape = tensor.shape
    dim_size = shape.dims[dim]
    
    # Calculate split size
    split_size = math.ceil(dim_size / chunks)
    
    return split(tensor, split_size, dim)


# Alias for backward compatibility
split_with_alias = split

class Sub(Function):
    """Elementwise subtraction with broadcasting."""

    name = "sub"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        left = a if isinstance(a, Tensor) else _as_tensor(a)
        right = b if isinstance(b, Tensor) else _as_tensor(b, left)
        dtype = left.dtype.promote(right.dtype)
        out = Tensor.from_numpy(
            np.subtract(left.numpy().astype(dtype.np_dtype, copy=False), right.numpy().astype(dtype.np_dtype, copy=False)),
            dtype,
            left.device,
        )
        return _maybe_require_grad(out, a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("a"), ctx.load("b")
        ga = unbroadcast(grad_output, a.shape) if isinstance(a, Tensor) else None
        gb = unbroadcast(-grad_output, b.shape) if isinstance(b, Tensor) else None
        return ga, gb


class Mul(Function):
    """Elementwise multiplication with broadcasting."""

    name = "mul"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        left = a if isinstance(a, Tensor) else _as_tensor(a)
        right = b if isinstance(b, Tensor) else _as_tensor(b, left)
        dtype = left.dtype.promote(right.dtype)
        out = Tensor.from_numpy(
            np.multiply(left.numpy().astype(dtype.np_dtype, copy=False), right.numpy().astype(dtype.np_dtype, copy=False)),
            dtype,
            left.device,
        )
        return _maybe_require_grad(out, a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("a"), ctx.load("b")
        if isinstance(a, Tensor) and isinstance(b, Tensor):
            return unbroadcast(grad_output * b, a.shape), unbroadcast(grad_output * a, b.shape)
        if isinstance(a, Tensor):
            # The other operand is a Python scalar, which has no gradient.
            return unbroadcast(grad_output * float(b), a.shape), None
        if isinstance(b, Tensor):
            return None, unbroadcast(grad_output * float(a), b.shape)
        return None, None


class Div(Function):
    """Elementwise division with broadcasting."""

    name = "div"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        left = a if isinstance(a, Tensor) else _as_tensor(a)
        right = b if isinstance(b, Tensor) else _as_tensor(b, left)
        dtype = left.dtype.promote(right.dtype)
        out = Tensor.from_numpy(
            np.divide(left.numpy().astype(dtype.np_dtype, copy=False), right.numpy().astype(dtype.np_dtype, copy=False)),
            dtype,
            left.device,
        )
        return _maybe_require_grad(out, a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("a"), ctx.load("b")
        if not isinstance(a, Tensor) and not isinstance(b, Tensor):
            return None, None
        if isinstance(a, Tensor) and isinstance(b, Tensor):
            ga = unbroadcast(grad_output / b, a.shape)
            gb = unbroadcast(-grad_output * a / (b * b), b.shape)
            return ga, gb
        if isinstance(a, Tensor):
            return unbroadcast(grad_output / b, a.shape), None
        return None, unbroadcast(-grad_output * a / (b * b), b.shape)


class Neg(Function):
    """Elementwise negation."""

    name = "neg"

    @staticmethod
    def forward(ctx, x):
        ctx.save(x=x)
        return Tensor.from_numpy(np.negative(x.numpy()), x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return (-grad_output,)


class Pow(Function):
    """Elementwise power with a scalar or tensor exponent."""

    name = "pow"

    @staticmethod
    def forward(ctx, x, exponent):
        ctx.save(x=x, exponent=exponent)
        array = x.numpy()
        if isinstance(exponent, Tensor):
            out_array = np.power(array, exponent.numpy())
        else:
            out_array = np.power(array, exponent)
        return Tensor.from_numpy(out_array, x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x, exponent = ctx.load("x"), ctx.load("exponent")
        if isinstance(exponent, Tensor):
            return grad_output * exponent * x ** (exponent - 1), grad_output * x.numpy() * np.log(
                x.numpy(), where=x.numpy() > 0, out=np.zeros_like(x.numpy())
            )
        return grad_output * float(exponent) * x ** (float(exponent) - 1), None


class MatMul(Function):
    """Matrix multiplication with NumPy batch semantics.

    1-D operands are treated as vectors, matching the convention used by most
    tensor libraries: ``matmul(vector, matrix)`` contracts the vector against
    the matrix's rows.
    """

    name = "matmul"

    @staticmethod
    def forward(ctx, a, b):
        ctx.save(a=a, b=b)
        out = Tensor.from_numpy(np.matmul(a.numpy(), b.numpy()), _promote(a.dtype, b.dtype), a.device)
        return out.requires_grad_(a.requires_grad or b.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.load("a"), ctx.load("b")
        grad = grad_output.numpy()
        if grad.ndim == 0:
            grad = grad.reshape(1, 1)

        a_was_vector = a.ndim == 1
        b_was_vector = b.ndim == 1
        a_batch = tuple(a.shape.dims[:-2]) if a.ndim > 1 else ()
        b_batch = tuple(b.shape.dims[:-2]) if b.ndim > 1 else ()
        batch = broadcast_shapes(Shape(a_batch), Shape(b_batch)).dims

        a_matrix = a.numpy()
        b_matrix = b.numpy()
        # A vector operand contracts differently from a matrix: matmul(a, v)
        # contracts a's last axis with v, while matmul(v, b) contracts v with
        # b's first axis. einsum states that directly. The batch axes are kept
        # in the result and summed afterwards, because einsum refuses to drop
        # a non-empty ellipsis implicitly.
        if b_was_vector and not a_was_vector:
            grad_a = np.einsum("...n,k->...nk", grad, b_matrix).reshape(a.shape.dims)
            grad_b = _sum_leading(np.einsum("...nk,...n->...k", a_matrix, grad))
        elif a_was_vector and not b_was_vector:
            grad_b = np.einsum("n,...m->...nm", a_matrix, grad).reshape(b.shape.dims)
            grad_a = _sum_leading(np.einsum("...nm,...m->...n", b_matrix, grad))
        else:
            # Restore the contracted dimension so the two matrices broadcast
            # the way they did in the forward pass. The rank must come from
            # .ndim: len() on an ndarray is its first axis, not its dimension
            # count, and using it here silently mis-pads batched gradients.
            grad_batched = grad
            if grad_batched.ndim < len(batch) + 2:
                pad = len(batch) + 2 - grad_batched.ndim
                grad_batched = grad_batched.reshape((1,) * pad + tuple(grad_batched.shape))
            grad_a = np.matmul(grad_batched, np.swapaxes(b_matrix, -1, -2))
            grad_b = np.matmul(np.swapaxes(a_matrix, -1, -2), grad_batched)

        # A weight is shared across every batch and position, so the batch
        # dimensions have to be summed away rather than kept.
        grad_a = _reduce_batch(grad_a, batch, a_batch, a_was_vector, a)
        grad_b = _reduce_batch(grad_b, batch, b_batch, b_was_vector, b)

        return (
            Tensor.from_numpy(grad_a, a.dtype, a.device) if grad_a is not None else None,
            Tensor.from_numpy(grad_b, b.dtype, b.device) if grad_b is not None else None,
        )


def _sum_leading(grad: np.ndarray) -> np.ndarray:
    """Sum every leading axis, leaving only the last one.

    A vector operand is shared across every batch entry, so its gradient is
    the total over the batch.
    """
    if grad.ndim <= 1:
        return grad
    return grad.sum(axis=tuple(range(grad.ndim - 1)))


def _reduce_batch(
    grad: np.ndarray | None,
    batch: tuple[int, ...],
    own_batch: tuple[int, ...],
    was_vector: bool,
    operand: Tensor,
) -> np.ndarray | None:
    """Sum a batched gradient down to the shape of its operand."""
    if grad is None:
        return None
    if was_vector:
        # A vector operand keeps only the contracted axis.
        return grad.reshape(-1)
    if len(own_batch) < len(batch):
        # Leading axes came from broadcasting the other operand, and this
        # operand did not have them, so they are summed out.
        grad = grad.sum(axis=tuple(range(len(batch) - len(own_batch))))
    return grad.reshape(operand.shape.dims)


class Sqrt(Function):
    """Square root."""

    name = "sqrt"

    @staticmethod
    def forward(ctx, x):
        ctx.save(x=x)
        out = Tensor.from_numpy(np.sqrt(x.numpy()), x.dtype, x.device)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x = ctx.load("x")
        return (grad_output / (2 * sqrt(x)),)


class Exp(Function):
    """Natural exponential."""

    name = "exp"

    @staticmethod
    def forward(ctx, x):
        # Computed directly rather than through the public exp() helper, which
        # would re-enter this forward and recurse forever.
        out = Tensor.from_numpy(np.exp(x.numpy()), x.dtype, x.device)
        ctx.save(out=out)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        # d(exp)/dx = exp(x), which is the forward output already saved.
        return (grad_output * ctx.load("out"),)


class Log(Function):
    """Natural logarithm."""

    name = "log"

    @staticmethod
    def forward(ctx, x):
        ctx.save(x=x)
        return Tensor.from_numpy(np.log(x.numpy()), x.dtype, x.device).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return (grad_output / ctx.load("x"),)


class BroadcastTensor(Function):
    """Expand a tensor to ``shape`` by adding axes and repeating elements."""

    name = "broadcast_to"

    @staticmethod
    def forward(ctx, x, shape):
        ctx.save(x=x, shape=shape)
        out = Tensor.from_numpy(np.broadcast_to(x.numpy(), tuple(shape.dims)).copy(), x.dtype, x.device)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return unbroadcast(grad_output, ctx.load("x").shape), None


def _promote(a: DType, b: DType) -> DType:
    """Return the dtype two operands promote to."""
    return a.promote(b)


def _maybe_require_grad(out: Tensor, *inputs: Any) -> Tensor:
    """Mark ``out`` as requiring grad when any input does."""
    if any(isinstance(i, Tensor) and i.requires_grad for i in inputs):
        out.requires_grad_(True)
    return out


# ----------------------------------------------------------------------
# Functional entry points
# ----------------------------------------------------------------------


def add(a: Tensor | float, b: Tensor | float) -> Tensor:
    """Elementwise ``a + b``."""
    return Add.apply(a, b)


def sub(a: Tensor | float, b: Tensor | float) -> Tensor:
    """Elementwise ``a - b``."""
    return Sub.apply(a, b)


def mul(a: Tensor | float, b: Tensor | float) -> Tensor:
    """Elementwise ``a * b``."""
    return Mul.apply(a, b)


def div(a: Tensor | float, b: Tensor | float) -> Tensor:
    """Elementwise ``a / b``."""
    return Div.apply(a, b)


def neg(a: Tensor) -> Tensor:
    """Elementwise ``-a``."""
    return Neg.apply(a)


def pow(a: Tensor, exponent: Tensor | float) -> Tensor:
    """Elementwise ``a ** exponent``."""
    return Pow.apply(a, exponent)


def matmul(a: Tensor, b: Tensor) -> Tensor:
    """Matrix product of ``a`` and ``b``."""
    return MatMul.apply(a, b)


def sqrt(a: Tensor) -> Tensor:
    """Elementwise square root."""
    return Sqrt.apply(a)


def exp(a: Tensor) -> Tensor:
    """Elementwise natural exponential."""
    return Exp.apply(a)


def log(a: Tensor) -> Tensor:
    """Elementwise natural logarithm."""
    return Log.apply(a)


def broadcast_tensor(a: Tensor, shape: Shape) -> Tensor:
    """Expand ``a`` to ``shape``."""
    return BroadcastTensor.apply(a, shape)


def expand(a: Tensor, shape: Sequence[int]) -> Tensor:
    """Expand ``a`` to ``shape`` by adding dimensions of size 1 and repeating elements."""
    from astrovox.tensor.shape import Shape
    return BroadcastTensor.apply(a, Shape(shape))


class Concat(Function):
    """Concatenate a sequence of tensors along a given axis."""

    name = "concat"

    @staticmethod
    def forward(ctx, tensors, axis):
        ctx.save(tensors=tensors, axis=axis)
        ndim = tensors[0].ndim
        axis = _normalize_axis(axis, ndim)
        ctx.axis = axis
        # Verify all tensors have the same number of dimensions
        for t in tensors[1:]:
            if t.ndim != ndim:
                raise ValueError(
                    f"Expected all tensors to have the same number of dimensions "
                    f"({ndim}), but got {t.ndim}"
                )
        # Check that the axis size is compatible for concatenation
        cat_size = sum(t.shape.dims[axis] for t in tensors)
        # Build the output shape
        shape_list = list(tensors[0].shape.dims)
        shape_list[axis] = cat_size
        out_shape = Shape(shape_list)
        # Concatenate using numpy
        arrays = [t.numpy() for t in tensors]
        out_array = np.concatenate(arrays, axis=axis)
        out = Tensor.from_numpy(out_array, tensors[0].dtype, tensors[0].device)
        return out.requires_grad_(any(t.requires_grad for t in tensors))

    @staticmethod
    def backward(ctx, grad_output):
        axis = ctx.axis
        tensors = ctx.load("tensors")
        grads = []
        # Split the gradient along the concatenation axis
        # We need to split grad_output into chunks corresponding to each tensor
        input_sizes = [t.shape.dims[axis] for t in tensors]
        # Use np.split to divide the gradient
        grad_arrays = np.split(grad_output.numpy(), input_sizes, axis=axis)
        for i, t in enumerate(tensors):
            grad = Tensor.from_numpy(grad_arrays[i], t.dtype, t.device)
            grads.append(grad.requires_grad_(t.requires_grad))
        return tuple(grads), None


def add_(a: Tensor, b: Tensor | float) -> Tensor:
    """In-place ``a += b``."""
    return a.add_(b)


def outer(a: Tensor, b: Tensor) -> Tensor:
    """Outer product of two vectors."""
    return matmul(a.reshape(-1, 1), b.reshape(1, -1))


def dot(a: Tensor, b: Tensor) -> Tensor:
    """Dot product of two vectors."""
    return (a * b).sum()


def square(a: Tensor) -> Tensor:
    """Elementwise ``a * a``."""
    return mul(a, a)


def reciprocal(a: Tensor) -> Tensor:
    """Elementwise ``1 / a``."""
    return div(Tensor.ones(a.shape.dims, a.dtype, a.device), a)


def repeat(x: Tensor, repeats: int | Sequence[int], axis: int | None = None) -> Tensor:
    """Repeat elements of a tensor along specified dimensions.

    Args:
        x: input tensor
        repeats: number of times to repeat each element, or a sequence of repeats
            per dimension
        axis: axis along which to repeat. If None, repeats along the last axis.

    Returns:
        tensor with repeated elements
    """
    return Repeat.apply(x, repeats, axis)


class Repeat(Function):
    """Repeat elements of a tensor along specified dimensions."""

    name = "repeat"

    @staticmethod
    def forward(ctx, x, repeats, axis=None):
        ctx.save(x=x, repeats=repeats, axis=axis)
        out = Tensor.from_numpy(
            np.repeat(x.numpy(), repeats, axis=axis),
            x.dtype,
            x.device,
        )
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        x, repeats, axis = ctx.load("x"), ctx.load("repeats"), ctx.load("axis")
        x_arr = x.numpy()
        grad = grad_output.numpy()
        ndim = x_arr.ndim

        if axis is None:
            axis = ndim - 1

        axis = axis if axis >= 0 else ndim + axis

        out_shape = list(np.repeat(x_arr.shape, repeats if isinstance(repeats, (int, tuple, list)) else 1, axis=axis).shape)
        # Determine the output shape along the repeated axis
        axis_size = x_arr.shape[axis]
        if isinstance(repeats, int) or (isinstance(repeats, (tuple, list)) and len(repeats) > 0 and axis < len(repeats)):
            r = repeats if isinstance(repeats, int) else repeats[axis] if axis < len(repeats) else 1
        else:
            r = 1

        # Build the index mapping for gradient scattering
        # Each input element at position i along axis contributes to r output positions
        # We need to sum grad_output across those r positions back to input position i

        # Create an index array that maps output positions -> input positions
        # Using np.repeat's inverse: for output position j, input position = j // r (along axis)
        # But we need to handle the multi-dimensional case properly

        # Reshape approach: collapse all dims except axis, do 1D scatter, reshape back
        if axis == ndim - 1:
            # Last axis case - simplest
            in_size = x_arr.shape[axis]
            out_size = in_size * r if isinstance(repeats, int) else in_size * (repeats[axis] if axis < len(repeats) else 1)

            # Create output indices: 0, 1, ..., out_size-1
            out_idx = np.arange(out_size, dtype=np.intp)

            # Map output indices to input indices: each input element repeats r times
            # input_idx = out_idx // r
            in_idx = out_idx // r

            # Scatter: grad_input[in_idx] += grad[out_idx]
            # Use np.bincount for efficient scattering
            grad_flat = grad.reshape(-1) if grad.ndim > 1 else grad
            in_size_total = x_arr.numel

            # Create a full gradient array initialized to zero
            grad_input = np.zeros_like(x_arr, dtype=grad.dtype)

            # Use np.add.at to scatter
            np.add.at(grad_input.reshape(-1), in_idx, grad_flat)

            # Reshape back to original shape
            grad_input = grad_input.reshape(x_arr.shape)
        else:
            # General case: need to handle non-last axis
            # Move the target axis to the last position, process, then move back
            # Permute so axis becomes the last dimension
            perm = list(range(ndim))
            perm[axis], perm[-1] = perm[-1], perm[axis]
            x_perm = np.transpose(x_arr, perm)
            grad_perm = np.transpose(grad, perm)

            # Now process along last axis
            in_size = x_perm.shape[-1]
            r_val = repeats if isinstance(repeats, int) else (repeats[axis] if isinstance(repeats, (tuple, list)) and axis < len(repeats) else 1)
            out_size = in_size * r_val

            out_idx = np.arange(out_size, dtype=np.intp)
            in_idx = out_idx // r_val

            grad_input_perm = np.zeros_like(x_perm, dtype=grad.dtype)
            grad_flat = grad_perm.reshape(-1) if grad_perm.ndim > 1 else grad_perm

            np.add.at(grad_input_perm.reshape(-1), in_idx, grad_flat)

            # Permute back
            grad_input = np.transpose(grad_input_perm, perm)

        return Tensor.from_numpy(grad_input, x.dtype, x.device),


class Stack(Function):
    """Stack a sequence of tensors along a new axis."""

    name = "stack"

    @staticmethod
    def forward(ctx, tensors, axis):
        ctx.save(tensors=tensors, axis=axis)
        dt = tensors[0].dtype
        device = tensors[0].device
        stacked = np.stack([t.numpy() for t in tensors], axis=axis)
        out = Tensor.from_numpy(stacked, dt, device)
        return out.requires_grad_(any(t.requires_grad for t in tensors))

    @staticmethod
    def backward(ctx, grad_output):
        tensors = ctx.load("tensors")
        axis = ctx.load("axis")
        grads = []
        for i, t in enumerate(tensors):
            # Build index tuple to select the i-th slice along axis
            # then remove the stacking axis by reshaping
            slices = [slice(None)] * grad_output.ndim
            slices[axis] = i
            gi = grad_output[numpy_index_tuple(slices)]
            # gi still has the stacking axis of size 1, squeeze it out
            gi = gi.reshape(t.shape.dims)
            grads.append(Tensor.from_numpy(gi, t.dtype, t.device))
        return tuple(grads), None


def numpy_index_tuple(slices):
    """Convert slice list to tuple for numpy indexing."""
    return tuple(slices)


def stack(tensors: Sequence[Tensor], axis: int = 0) -> Tensor:
    """Stack a sequence of tensors along a new axis.

    Args:
        tensors: sequence of tensors to stack. All must have the same shape.
        axis: axis along which to stack. Negative values are supported.

    Returns:
        A tensor with the stacked data, with the stacking axis inserted at ``axis``.
    """
    from astrovox.autograd.function import current_graph

    # Normalize axis
    ndim = max(t.ndim for t in tensors)
    axis = axis if axis >= 0 else axis + ndim + 1

    graph = current_graph()
    result = Stack.apply(tensors, axis)

    if graph.is_enabled() and result.requires_grad:
        pass  # graph node already created by Stack.apply

    return result


def tile(x: Tensor, reps: Sequence[int]) -> Tensor:
    """Tile ``x`` along each dimension according to ``reps``."""
    return Tile.apply(x, reps)


class Tile(Function):
    """Tile an array by repeating elements along specified dimensions."""

    name = "tile"

    @staticmethod
    def forward(ctx, x, reps):
        ctx.save(x=x, reps=reps)
        out = Tensor.from_numpy(np.tile(x.numpy(), reps), x.dtype, x.device)
        return out.requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return (grad_output, None)


def split(tensor, split_size: int, dim: int = 0) -> list:
    """Split a tensor into chunks along dimension dim.

    Args:
        tensor: The tensor to split
        split_size: Size of each chunk
        dim: Dimension along which to split

    Returns:
        List of tensors resulting from the split
    """

    dim = _normalize_axis(dim, tensor.ndim)
    shape = tensor.shape
    dim_size = shape.dims[dim]

    # Calculate number of splits
    num_splits = (dim_size + split_size - 1) // split_size

    result = []
    for i in range(num_splits):
        start = i * split_size
        end = min((i + 1) * split_size, dim_size)

        # Create a slice key
        key = [slice(None)] * tensor.ndim
        key[dim] = slice(start, end)

        # Get the split tensor
        split_tensor = tensor[tuple(key)]
        result.append(split_tensor)

    return result


def chunk(tensor, chunks: int, dim: int = 0) -> list:
    """Split a tensor into roughly equal chunks along dimension dim.

    Args:
        tensor: The tensor to chunk
        chunks: Number of chunks
        dim: Dimension along which to chunk

    Returns:
        List of tensors resulting from the chunk
    """
    from astrovox.tensor.tensor import Tensor

    dim = _normalize_axis(dim, tensor.ndim)
    shape = tensor.shape
    dim_size = shape.dims[dim]

    # Calculate split size
    split_size = math.ceil(dim_size / chunks)

    return split(tensor, split_size, dim)
    """Elementwise modulo ``a % b``.

    Args:
        a: The dividend tensor
        b: The divisor tensor

    Returns:
        Result tensor with modulo of elements
    """
    import numpy as np

    from astrovox.tensor.dtype import DEFAULT

    # Ensure both are tensors
    if not isinstance(a, Tensor):
        a = Tensor.from_numpy(np.asarray(a), DEFAULT, CPU)
    if not isinstance(b, Tensor):
        b = Tensor.from_numpy(np.asarray(b), DEFAULT, CPU)

    # Promote dtypes
    dtype = a.dtype.promote(b.dtype)

    # Convert to common dtype
    a_arr = a.numpy().astype(dtype.np_dtype, copy=False)
    b_arr = b.numpy().astype(dtype.np_dtype, copy=False)

    # Handle modulo operation
    with np.errstate(divide='ignore', invalid='ignore'):
        result_arr = np.mod(a_arr, b_arr)

    out = Tensor.from_numpy(result_arr, dtype, a.device)
    return out.requires_grad_(a.requires_grad or b.requires_grad)
def mse_loss(input: Tensor, target: Tensor) -> Tensor:
    """Mean Squared Error loss."""
    import numpy as np

    from astrovox.tensor.dtype import DEFAULT
    from astrovox.tensor.tensor import Tensor
    
    if not isinstance(input, Tensor):
        input = tensor(input, DEFAULT, tensor.CPU)
    if not isinstance(target, Tensor):
        target = tensor(target, DEFAULT, tensor.CPU)
    
    dtype = input.dtype.promote(target.dtype)
    input_arr = input.numpy().astype(dtype.np_dtype, copy=False)
    target_arr = target.numpy().astype(dtype.np_dtype, copy=False)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        diff = input_arr - target_arr
        squared = diff ** 2
        mean = np.mean(squared)
    
    out = tensor.from_numpy(np.array([mean]), dtype, input.device)
    return out.requires_grad_(input.requires_grad or target.requires_grad)


def l1_loss(input: Tensor, target: Tensor) -> Tensor:
    """Mean Absolute Error loss (L1 loss)."""
    import numpy as np

    from astrovox.tensor.dtype import DEFAULT
    from astrovox.tensor.tensor import Tensor
    
    if not isinstance(input, Tensor):
        input = tensor(input, DEFAULT, tensor.CPU)
    if not isinstance(target, Tensor):
        target = tensor(target, DEFAULT, tensor.CPU)
    
    dtype = input.dtype.promote(target.dtype)
    input_arr = input.numpy().astype(dtype.np_dtype, copy=False)
    target_arr = target.numpy().astype(dtype.np_dtype, copy=False)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        diff = input_arr - target_arr
        abs_diff = np.abs(diff)
        mean = np.mean(abs_diff)
    
    out = tensor.from_numpy(np.array([mean]), dtype, input.device)
    return out.requires_grad_(input.requires_grad or target.requires_grad)


def cross_entropy(input: Tensor, target: Tensor) -> Tensor:
    """Cross Entropy loss."""
    import numpy as np

    from astrovox.tensor.dtype import DEFAULT
    from astrovox.tensor.tensor import Tensor
    
    if not isinstance(input, Tensor):
        input = tensor(input, DEFAULT, tensor.CPU)
    if not isinstance(target, Tensor):
        target = tensor(target, DEFAULT, tensor.CPU)
    
    dtype = input.dtype.promote(target.dtype)
    input_arr = input.numpy().astype(dtype.np_dtype, copy=False)
    target_arr = target.numpy().astype(dtype.np_dtype, copy=False)
    
    n = input_arr.shape[0]
    c = input_arr.shape[1]
    
    input_stable = input_arr - np.max(input_arr, axis=1, keepdims=True)
    exp_scores = np.exp(input_stable)
    probs = exp_scores / np.sum(exp_scores, axis=1, keepdims=True)
    
    correct_probs = probs[np.arange(n), target_arr.astype(int)]
    
    with np.errstate(divide='ignore', invalid='ignore'):
        log_likelihood = -np.log(correct_probs + 1e-10)
        mean_loss = np.mean(log_likelihood)
    
    out = tensor.from_numpy(np.array([mean_loss]), dtype, input.device)
    return out.requires_grad_(input.requires_grad or target.requires_grad)


def bce_loss(input: Tensor, target: Tensor) -> Tensor:
    """Binary Cross Entropy loss."""
    import numpy as np

    from astrovox.tensor.dtype import DEFAULT
    from astrovox.tensor.tensor import Tensor
    
    if not isinstance(input, Tensor):
        input = tensor(input, DEFAULT, tensor.CPU)
    if not isinstance(target, Tensor):
        target = tensor(target, DEFAULT, tensor.CPU)
    
    dtype = input.dtype.promote(target.dtype)
    input_arr = input.numpy().astype(dtype.np_dtype, copy=False)
    target_arr = target.numpy().astype(dtype.np_dtype, copy=False)
    
    input_clipped = np.clip(input_arr, -100, 100)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        bce = -((target_arr * np.log(input_clipped + 1e-10)) + 
                ((1 - target_arr) * np.log(1 - input_clipped + 1e-10)))
        mean_bce = np.mean(bce)
    
    out = tensor.from_numpy(np.array([mean_bce]), dtype, input.device)
    return out.requires_grad_(input.requires_grad or target.requires_grad)


def huber_loss(input: Tensor, target: Tensor, delta: float = 1.0) -> Tensor:
    """Huber loss (Huber quantile loss)."""
    import numpy as np

    from astrovox.tensor.dtype import DEFAULT
    from astrovox.tensor.tensor import Tensor
    
    if not isinstance(input, Tensor):
        input = tensor(input, DEFAULT, tensor.CPU)
    if not isinstance(target, Tensor):
        target = tensor(target, DEFAULT, tensor.CPU)
    
    dtype = input.dtype.promote(target.dtype)
    input_arr = input.numpy().astype(dtype.np_dtype, copy=False)
    target_arr = target.numpy().astype(dtype.np_dtype, copy=False)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        diff = input_arr - target_arr
        abs_diff = np.abs(diff)
        huber = np.where(abs_diff <= delta,
                         0.5 * diff ** 2,
                         delta * (abs_diff - 0.5 * delta))
        mean_huber = np.mean(huber)
    
    out = tensor.from_numpy(np.array([mean_huber]), dtype, input.device)
    return out.requires_grad_(input.requires_grad or target.requires_grad)


def smooth_l1_loss(input: Tensor, target: Tensor, beta: float = 1.0) -> Tensor:
    """Smooth L1 loss (also known as Huber loss or CIELoss)."""
    import numpy as np

    from astrovox.tensor.dtype import DEFAULT
    from astrovox.tensor.tensor import Tensor
    
    if not isinstance(input, Tensor):
        input = tensor(input, DEFAULT, tensor.CPU)
    if not isinstance(target, Tensor):
        target = tensor(target, DEFAULT, tensor.CPU)
    
    dtype = input.dtype.promote(target.dtype)
    input_arr = input.numpy().astype(dtype.np_dtype, copy=False)
    target_arr = target.numpy().astype(dtype.np_dtype, copy=False)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        diff = np.abs(input_arr - target_arr)
        loss = np.where(diff < beta, 0.5 * diff ** 2 / beta, diff - 0.5 * beta)
        mean_loss = np.mean(loss)
    
    out = tensor.from_numpy(np.array([mean_loss]), dtype, input.device)
    return out.requires_grad_(input.requires_grad or target.requires_grad)

# Optimizer classes for Astrovox

class Optimizer:
    """Base optimizer class."""
    
    def __init__(self, params, lr=1e-3):
        self.params = list(params)
        self.lr = lr
        self.step_count = 0
    
    def zero_grad(self):
        for p in self.params:
            if hasattr(p, 'grad') and p.grad is not None:
                p.grad.zero_()
    
    def step(self):
        self.step_count += 1
    
    def lr_schedule(self, step):
        return self.lr


class SGD(Optimizer):
    """Stochastic Gradient Descent with optional momentum and Nesterov acceleration."""
    
    def __init__(self, params, lr=0.01, momentum=0.0, dampening=0.0, weight_decay=0.0, nesterov=False):
        super().__init__(params, lr)
        self.momentum = momentum
        self.dampening = dampening
        self.weight_decay = weight_decay
        self.nesterov = nesterov
        self.velocity = [None] * len(self.params)
    
    def step(self):
        self.step_count += 1
        for i, p in enumerate(self.params):
            if p.grad is None:
                continue
            
            d_p = p.grad
            
            # Apply weight decay
            if self.weight_decay != 0:
                d_p = d_p.add(p.data, alpha=self.weight_decay)
            
            if self.momentum != 0:
                if self.velocity[i] is None:
                    self.velocity[i] = d_p.clone()
                else:
                    self.velocity[i].mul_(self.momentum).add_(d_p, alpha=1 - self.dampening)
                
                if self.nesterov:
                    d_p = self.velocity[i] + self.momentum * self.velocity[i]
                else:
                    d_p = self.velocity[i]
            
            p.data.add_(d_p, alpha=-self.lr)
    
    def lr_schedule(self, step):
        return self.lr * (1 + np.cos(np.pi * step / 100)) / 2


class Adam(Optimizer):
    """Adam optimizer."""
    
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.0):
        super().__init__(params, lr)
        self.betas = betas
        self.eps = eps
        self.weight_decay = weight_decay
        self.m = [None] * len(self.params)
        self.v = [None] * len(self.params)
        self.t = 0
    
    def step(self):
        self.step_count += 1
        self.t += 1
        
        for i, p in enumerate(self.params):
            if p.grad is None:
                continue
            
            d_p = p.grad
            
            if self.weight_decay != 0:
                d_p = d_p.add(p.data, alpha=self.weight_decay)
            
            if self.m[i] is None:
                self.m[i] = d_p.clone()
            else:
                self.m[i].mul_(self.betas[0]).add_(d_p, alpha=1 - self.betas[0])
            
            if self.v[i] is None:
                self.v[i] = d_p.clone() ** 2
            else:
                self.v[i].mul_(self.betas[1]).add_(d_p ** 2, alpha=1 - self.betas[1])
            
            m_hat = self.m[i] / (1 - self.betas[0] ** self.t)
            v_hat = self.v[i] / (1 - self.betas[1] ** self.t)
            
            p.data.add_(m_hat, alpha=-self.lr / (v_hat.sqrt() + self.eps))
    
    def lr_schedule(self, step):
        return self.lr * (1 + np.cos(np.pi * step / 100)) / 2


class AdamW(Optimizer):
    """AdamW optimizer with decoupled weight decay."""
    
    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8, weight_decay=0.01):
        super().__init__(params, lr)
        self.betas = betas
        self.eps = eps
        self.weight_decay = weight_decay
        self.m = [None] * len(self.params)
        self.v = [None] * len(self.params)
        self.t = 0
    
    def step(self):
        self.step_count += 1
        self.t += 1
        
        for i, p in enumerate(self.params):
            if p.grad is None:
                continue
            
            d_p = p.grad
            
            if self.weight_decay != 0:
                p.mul_(1 - self.lr * self.weight_decay)
            
            if self.m[i] is None:
                self.m[i] = d_p.clone()
            else:
                self.m[i].mul_(self.betas[0]).add_(d_p, alpha=1 - self.betas[0])
            
            if self.v[i] is None:
                self.v[i] = d_p.clone() ** 2
            else:
                self.v[i].mul_(self.betas[1]).add_(d_p ** 2, alpha=1 - self.betas[1])
            
            m_hat = self.m[i] / (1 - self.betas[0] ** self.t)
            v_hat = self.v[i] / (1 - self.betas[1] ** self.t)
            
            p.data.add_(m_hat, alpha=-self.lr / (v_hat.sqrt() + self.eps))
    
    def lr_schedule(self, step):
        return self.lr * (1 + np.cos(np.pi * step / 100)) / 2


class RMSProp(Optimizer):
    """RMSProp optimizer."""
    
    def __init__(self, params, lr=1e-2, alpha=0.99, eps=1e-8, weight_decay=0.0):
        super().__init__(params, lr)
        self.alpha = alpha
        self.eps = eps
        self.weight_decay = weight_decay
        self.m = [None] * len(self.params)
    
    def step(self):
        self.step_count += 1
        
        for i, p in enumerate(self.params):
            if p.grad is None:
                continue
            
            d_p = p.grad
            
            if self.weight_decay != 0:
                d_p = d_p.add(p.data, alpha=self.weight_decay)
            
            if self.m[i] is None:
                self.m[i] = d_p ** 2
            else:
                self.m[i].mul_(self.alpha).add_(d_p ** 2, alpha=1 - self.alpha)
            
            p.data.add_(d_p, alpha=-self.lr / (self.m[i].sqrt() + self.eps))


class Lookahead(Optimizer):
    """Lookahead optimizer wrapper."""
    
    def __init__(self, optimizer, k=5, alpha=0.5):
        super().__init__(optimizer.params, optimizer.lr)
        self.optimizer = optimizer
        self.k = k
        self.alpha = alpha
        self.slow_weights = [None] * len(self.params)
        self.step_count = 0
    
    def step(self):
        self.step_count += 1
        self.optimizer.step()
        
        for i, p in enumerate(self.params):
            if self.slow_weights[i] is None:
                self.slow_weights[i] = p.data.clone()
            
            p.data.lerp_(self.slow_weights[i], self.alpha)
            
            if self.step_count % self.k == 0:
                self.slow_weights[i] = p.data.clone()
    
    def lr_schedule(self, step):
        return self.optimizer.lr_schedule(step)


# Aliases
SGD = SGD
Momentum = SGD
Nesterov = lambda params, lr=0.01, momentum=0.9, weight_decay=0.0, **kwargs: SGD(params, lr, momentum, weight_decay=weight_decay, nesterov=True)
Adam = Adam
AdamW = AdamW
RMSProp = RMSProp
Lion = None  # Placeholder
LAMB = None  # Placeholder


__all__ = [
    "Optimizer",
    "SGD",
    "Momentum",
    "Nesterov",
    "Adam",
    "AdamW",
    "RMSProp",
    "Lion",
    "LAMB",
    "Lookahead",
    "add",
    "sub",
    "mul",
    "div",
    "neg",
    "pow",
    "dot",
    "square",
    "reciprocal",
    "mse_loss",
    "l1_loss",
    "cross_entropy",
    "bce_loss",
    "huber_loss",
    "smooth_l1_loss",
    "mod",
]