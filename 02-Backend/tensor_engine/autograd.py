import numpy as np
from collections import deque


class Tensor:
    def __init__(self, data, requires_grad=False, grad_fn=None, ctx=None):
        if isinstance(data, Tensor):
            self.data = data.data.copy()
            self.requires_grad = requires_grad or data.requires_grad
        else:
            self.data = np.asarray(data, dtype=np.float64)
            self.requires_grad = requires_grad
        self.grad = np.zeros_like(self.data, dtype=np.float64) if self.requires_grad else None
        self.grad_fn = grad_fn
        self.ctx = ctx

    def __repr__(self):
        return f"Tensor({self.data}, requires_grad={self.requires_grad})"

    def zero_grad(self):
        if self.requires_grad:
            self.grad = np.zeros_like(self.data, dtype=np.float64)

    def backward(self, grad_output=None):
        if not self.requires_grad:
            raise RuntimeError("Cannot call backward on a tensor that doesn't require grad")
        
        if grad_output is None:
            grad_output = np.ones_like(self.data, dtype=np.float64)
        else:
            grad_output = np.asarray(grad_output, dtype=np.float64)
        
        nodes = []
        visited = set()
        
        def build_graph(tensor):
            if id(tensor) in visited:
                return
            visited.add(id(tensor))
            nodes.append(tensor)
            if tensor.grad_fn is not None:
                for inp in tensor.grad_fn.inputs:
                    if inp is not None and isinstance(inp, Tensor):
                        build_graph(inp)
        
        build_graph(self)
        topo_order = _topological_sort(nodes)
        self.grad = grad_output.copy()
        
        for node in reversed(topo_order):
            if node.grad_fn is not None and node.requires_grad:
                local_grads = node.grad_fn.backward(node.ctx, node.grad)
                for inp, g in zip(node.grad_fn.inputs, local_grads):
                    if inp is not None and inp.requires_grad and g is not None:
                        if inp.grad is None:
                            inp.grad = np.zeros_like(inp.data, dtype=np.float64)
                        inp.grad = inp.grad + g

    def __add__(self, other):
        other = _to_tensor(other)
        return Add.apply(self, other)

    def __radd__(self, other):
        return self.__add__(other)

    def __mul__(self, other):
        other = _to_tensor(other)
        return Mul.apply(self, other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __matmul__(self, other):
        other = _to_tensor(other)
        return MatMul.apply(self, other)

    def __pow__(self, other):
        other = _to_tensor(other)
        return Pow.apply(self, other)

    def __truediv__(self, other):
        other = _to_tensor(other)
        return Mul.apply(self, Pow.apply(other, Tensor(np.array(-1.0))))

    def __neg__(self):
        return Mul.apply(self, Tensor(np.array(-1.0)))

    def __sub__(self, other):
        other = _to_tensor(other)
        return Add.apply(self, -other)

    def exp(self):
        return Exp.apply(self)

    def log(self):
        return Log.apply(self)

    def sum(self, dim=None, keepdim=False):
        return Sum.apply(self, dim, keepdim)

    def mean(self, dim=None, keepdim=False):
        return Mean.apply(self, dim, keepdim)

    def max(self, dim=None, keepdim=False):
        return Max.apply(self, dim, keepdim)

    def relu(self):
        return ReLU.apply(self)

    def sigmoid(self):
        return Sigmoid.apply(self)

    def tanh(self):
        return Tanh.apply(self)

    def gelu(self):
        return GELU.apply(self)

    def swish(self):
        return Swish.apply(self)

    def softmax(self, dim=-1):
        return Softmax.apply(self, dim)

    def layer_norm(self, normalized_shape, eps=1e-5):
        return LayerNorm.apply(self, normalized_shape, eps)

    def rms_norm(self, normalized_shape, eps=1e-5):
        return RMSNorm.apply(self, normalized_shape, eps)

    def reshape(self, *shape):
        return Reshape.apply(self, shape)

    def transpose(self, dim0, dim1):
        return Transpose.apply(self, dim0, dim1)

    def detach(self):
        return Tensor(self.data.copy(), requires_grad=False)


def _to_tensor(x):
    if isinstance(x, Tensor):
        return x
    return Tensor(np.asarray(x, dtype=np.float64))


def _unbroadcast(grad, shape):
    while grad.ndim > len(shape):
        grad = grad.sum(axis=0)
    for i, (g, s) in enumerate(zip(grad.shape, shape)):
        if g != s:
            grad = grad.sum(axis=i, keepdims=True)
    return grad


def _topological_sort(nodes):
    visited = set()
    result = []
    
    def visit(node):
        if id(node) in visited:
            return
        visited.add(id(node))
        if node.grad_fn is not None:
            for inp in node.grad_fn.inputs:
                if inp is not None and isinstance(inp, Tensor):
                    visit(inp)
        result.append(node)
    
    for node in nodes:
        visit(node)
    
    return result


class Function:
    @classmethod
    def apply(cls, *inputs):
        ctx = cls()
        inputs = [_to_tensor(x) for x in inputs]
        ctx.inputs = inputs
        requires_grad = any(x.requires_grad for x in inputs)
        data = cls.forward(ctx, *[x.data for x in inputs])
        return Tensor(data, requires_grad=requires_grad, grad_fn=ctx if requires_grad else None, ctx=ctx)

    @staticmethod
    def forward(ctx, *inputs):
        raise NotImplementedError

    @staticmethod
    def backward(ctx, grad_output):
        raise NotImplementedError


class Add(Function):
    @staticmethod
    def forward(ctx, a, b):
        return a + b

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.inputs
        grad_a = _unbroadcast(grad_output, a.data.shape)
        grad_b = _unbroadcast(grad_output, b.data.shape)
        return grad_a, grad_b


class Mul(Function):
    @staticmethod
    def forward(ctx, a, b):
        ctx.save_a = a
        ctx.save_b = b
        return a * b

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.save_a, ctx.save_b
        grad_a = grad_output * b
        grad_b = grad_output * a
        grad_a = _unbroadcast(grad_a, a.shape)
        grad_b = _unbroadcast(grad_b, b.shape)
        return grad_a, grad_b


class MatMul(Function):
    @staticmethod
    def forward(ctx, a, b):
        ctx.save_a = a
        ctx.save_b = b
        return np.matmul(a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.save_a, ctx.save_b
        grad_a = np.matmul(grad_output, np.swapaxes(b, -1, -2))
        grad_b = np.matmul(np.swapaxes(a, -1, -2), grad_output)
        return grad_a, grad_b


class Pow(Function):
    @staticmethod
    def forward(ctx, a, b):
        ctx.save_a = a
        ctx.save_b = b
        return np.power(a, b)

    @staticmethod
    def backward(ctx, grad_output):
        a, b = ctx.save_a, ctx.save_b
        grad_a = grad_output * b * np.power(a, b - 1)
        grad_b = grad_output * np.power(a, b) * np.log(np.where(a > 0, a, 1e-12))
        return grad_a, grad_b


class Exp(Function):
    @staticmethod
    def forward(ctx, a):
        ctx.save = a
        return np.exp(a)

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.save
        return grad_output * np.exp(a),


class Log(Function):
    @staticmethod
    def forward(ctx, a):
        ctx.save = a
        return np.log(np.where(a > 0, a, 1e-12))

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.save
        return grad_output / np.where(a > 0, a, 1e-12),


class Sum(Function):
    @classmethod
    def apply(cls, a, dim=None, keepdim=False):
        ctx = cls()
        a = _to_tensor(a)
        ctx.inputs = [a]
        ctx.dim = dim
        ctx.keepdim = keepdim
        requires_grad = a.requires_grad
        data = np.sum(a.data, axis=dim, keepdims=keepdim)
        return Tensor(data, requires_grad=requires_grad, grad_fn=ctx if requires_grad else None, ctx=ctx)

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.inputs[0]
        dim = ctx.dim
        keepdim = ctx.keepdim
        if dim is not None:
            grad = np.expand_dims(grad_output, axis=dim) if not keepdim else grad_output
            return np.broadcast_to(grad, a.data.shape).copy(),
        return np.ones_like(a.data, dtype=np.float64) * grad_output.sum(),


class Mean(Function):
    @classmethod
    def apply(cls, a, dim=None, keepdim=False):
        ctx = cls()
        a = _to_tensor(a)
        ctx.inputs = [a]
        ctx.dim = dim
        ctx.keepdim = keepdim
        requires_grad = a.requires_grad
        data = np.mean(a.data, axis=dim, keepdims=keepdim)
        return Tensor(data, requires_grad=requires_grad, grad_fn=ctx if requires_grad else None, ctx=ctx)

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.inputs[0]
        dim = ctx.dim
        keepdim = ctx.keepdim
        if dim is not None:
            n = a.data.shape[dim] if isinstance(dim, int) else int(np.prod([a.data.shape[d] for d in dim]))
            grad = np.expand_dims(grad_output, axis=dim) if not keepdim else grad_output
            return np.broadcast_to(grad, a.data.shape).copy() / float(n),
        return np.ones_like(a.data, dtype=np.float64) * grad_output.sum() / float(a.data.size),


class Max(Function):
    @classmethod
    def apply(cls, a, dim=None, keepdim=False):
        ctx = cls()
        a = _to_tensor(a)
        ctx.inputs = [a]
        ctx.dim = dim
        ctx.keepdim = keepdim
        requires_grad = a.requires_grad
        data = np.max(a.data, axis=dim, keepdims=keepdim)
        return Tensor(data, requires_grad=requires_grad, grad_fn=ctx if requires_grad else None, ctx=ctx)

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.inputs[0]
        dim = ctx.dim
        keepdim = ctx.keepdim
        if dim is not None:
            max_vals = np.max(a.data, axis=dim, keepdims=True)
            mask = (a.data == max_vals).astype(np.float64)
            grad = np.expand_dims(grad_output, axis=dim) if not keepdim else grad_output
            return np.broadcast_to(grad, a.data.shape).copy() * mask / mask.sum(axis=dim, keepdims=True),
        return np.zeros_like(a.data, dtype=np.float64),


class ReLU(Function):
    @staticmethod
    def forward(ctx, a):
        ctx.save = a
        return np.maximum(a, 0)

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.save
        return grad_output * (a > 0).astype(np.float64),


class Sigmoid(Function):
    @staticmethod
    def forward(ctx, a):
        ctx.save = a
        return 1.0 / (1.0 + np.exp(-a))

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.save
        s = 1.0 / (1.0 + np.exp(-a))
        return grad_output * s * (1 - s),


class Tanh(Function):
    @staticmethod
    def forward(ctx, a):
        ctx.save = a
        return np.tanh(a)

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.save
        return grad_output * (1 - np.tanh(a) ** 2),


class GELU(Function):
    @staticmethod
    def forward(ctx, a):
        ctx.save = a
        return 0.5 * a * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (a + 0.044715 * a ** 3)))

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.save
        cdf = 0.5 * (1.0 + np.tanh(np.sqrt(2.0 / np.pi) * (a + 0.044715 * a ** 3)))
        pdf = cdf * (1 - cdf)
        tanh_arg = np.sqrt(2.0 / np.pi) * (a + 0.044715 * a ** 3)
        dtanh = 1 - np.tanh(tanh_arg) ** 2
        derivative = cdf + a * pdf * np.sqrt(2.0 / np.pi) * (1 + 3 * 0.044715 * a ** 2) * dtanh
        return grad_output * derivative,


class Swish(Function):
    @staticmethod
    def forward(ctx, a):
        ctx.save = a
        s = 1.0 / (1.0 + np.exp(-a))
        return a * s

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.save
        s = 1.0 / (1.0 + np.exp(-a))
        return grad_output * (s + a * s * (1 - s)),


class Softmax(Function):
    @classmethod
    def apply(cls, a, dim=-1):
        ctx = cls()
        a = _to_tensor(a)
        ctx.inputs = [a]
        ctx.dim = dim
        requires_grad = a.requires_grad
        max_val = np.max(a.data, axis=dim, keepdims=True)
        exp_data = np.exp(a.data - max_val)
        ctx.output = exp_data / np.sum(exp_data, axis=dim, keepdims=True)
        return Tensor(ctx.output, requires_grad=requires_grad, grad_fn=ctx if requires_grad else None, ctx=ctx)

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.inputs[0]
        dim = ctx.dim
        s = ctx.output
        return (grad_output - np.sum(grad_output * s, axis=dim, keepdims=True)) * s,


class LayerNorm(Function):
    @staticmethod
    def forward(ctx, a, normalized_shape, eps=1e-5):
        ctx.save = a
        ctx.normalized_shape = normalized_shape
        ctx.eps = eps
        
        shape = a.shape
        ndim = len(shape)
        axis = tuple(range(ndim - len(normalized_shape), ndim))
        
        mean = np.mean(a, axis=axis, keepdims=True)
        var = np.var(a, axis=axis, keepdims=True)
        inv_std = 1.0 / np.sqrt(var + eps)
        
        ctx.save_mean = mean
        ctx.save_inv_std = inv_std
        
        return (a - mean) * inv_std

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.save
        mean = ctx.save_mean
        inv_std = ctx.save_inv_std
        normalized_shape = ctx.normalized_shape
        
        ndim = len(a.shape)
        axis = tuple(range(ndim - len(normalized_shape), ndim))
        
        n = np.prod([a.shape[d] for d in axis])
        
        grad = inv_std * (grad_output - np.mean(grad_output, axis=axis, keepdims=True) - 
                         (a - mean) * inv_std ** 2 * np.mean(grad_output * (a - mean), axis=axis, keepdims=True))
        return grad,


class RMSNorm(Function):
    @staticmethod
    def forward(ctx, a, normalized_shape, eps=1e-5):
        ctx.save = a
        ctx.normalized_shape = normalized_shape
        ctx.eps = eps
        
        ndim = len(a.shape)
        axis = tuple(range(ndim - len(normalized_shape), ndim))
        
        rms = np.sqrt(np.mean(a ** 2, axis=axis, keepdims=True) + eps)
        ctx.save_rms = rms
        
        return a / rms

    @staticmethod
    def backward(ctx, grad_output):
        a = ctx.save
        rms = ctx.save_rms
        normalized_shape = ctx.normalized_shape
        
        ndim = len(a.shape)
        axis = tuple(range(ndim - len(normalized_shape), ndim))
        
        n = np.prod([a.shape[d] for d in axis])
        
        grad = (rms * grad_output - a * np.mean(grad_output * a, axis=axis, keepdims=True) / (rms ** 2)) / (rms ** 2)
        return grad,


class Reshape(Function):
    @classmethod
    def apply(cls, a, shape):
        ctx = cls()
        a = _to_tensor(a)
        ctx.inputs = [a]
        ctx.original_shape = a.data.shape
        requires_grad = a.requires_grad
        data = a.data.reshape(shape)
        return Tensor(data, requires_grad=requires_grad, grad_fn=ctx if requires_grad else None, ctx=ctx)

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output.reshape(ctx.original_shape),


class Transpose(Function):
    @classmethod
    def apply(cls, a, dim0, dim1):
        ctx = cls()
        a = _to_tensor(a)
        dim0 = int(dim0)
        dim1 = int(dim1)
        ctx.inputs = [a]
        ctx.dim0 = dim0
        ctx.dim1 = dim1
        requires_grad = a.requires_grad
        ndim = len(a.data.shape)
        perm = list(range(ndim))
        perm[dim0], perm[dim1] = perm[dim1], perm[dim0]
        ctx.perm = tuple(perm)
        data = np.transpose(a.data, perm)
        return Tensor(data, requires_grad=requires_grad, grad_fn=ctx if requires_grad else None, ctx=ctx)

    @staticmethod
    def backward(ctx, grad_output):
        return np.transpose(grad_output, ctx.perm),
