import numpy as np


class BroadcastInfo:
    def __init__(self, shape_a, shape_b):
        self.shape_a = tuple(shape_a)
        self.shape_b = tuple(shape_b)
        self.ndim = max(len(shape_a), len(shape_b))
        self.result_shape = []

        for i in range(self.ndim):
            a = self.shape_a[i - (self.ndim - len(self.shape_a))] if i >= self.ndim - len(self.shape_a) else 1
            b = self.shape_b[i - (self.ndim - len(self.shape_b))] if i >= self.ndim - len(self.shape_b) else 1
            if a == 1:
                self.result_shape.append(b)
            elif b == 1:
                self.result_shape.append(a)
            elif a == b:
                self.result_shape.append(a)
            else:
                raise ValueError(
                    f"Cannot broadcast shapes {self.shape_a} and {self.shape_b} "
                    f"at dimension {i}: {a} vs {b}"
                )

        self.result_shape = tuple(self.result_shape)

    def stride_for(self, shape):
        strides = []
        for i in range(len(shape)):
            if shape[i] == 1:
                strides.append(0)
            else:
                stride = 1
                for j in range(i + 1, len(shape)):
                    stride *= shape[j]
                strides.append(stride)
        return tuple(strides)

    def has_overlap(self, shape_a, shape_b, strides_a, strides_b):
        for i in range(self.ndim):
            a_dim = shape_a[i - (self.ndim - len(shape_a))] if i >= self.ndim - len(shape_a) else 1
            b_dim = shape_b[i - (self.ndim - len(shape_b))] if i >= self.ndim - len(shape_b) else 1
            
            if a_dim == 1 and b_dim == 1:
                continue
            if a_dim == 1 and strides_a[i] == 0:
                if strides_b[i] != 0:
                    return False
                continue
            if b_dim == 1 and strides_b[i] == 0:
                if strides_a[i] != 0:
                    return False
                continue
            if a_dim == b_dim and strides_a[i] == strides_b[i]:
                continue
            
            return False
        return True

    def reduce_gradient(self, grad, original_shape):
        """Sum grad over broadcasted dimensions to match original shape."""
        original_shape = tuple(original_shape)
        if grad.shape == original_shape:
            return grad
        
        if not original_shape:
            return np.array(grad.sum())
        
        axes = []
        for i, (gs, os) in enumerate(zip(grad.shape, original_shape)):
            if os == 1 and gs > 1:
                axes.append(i)
        
        if axes:
            grad = np.sum(grad, axis=tuple(axes), keepdims=True)
        
        if grad.shape != original_shape:
            grad = np.reshape(grad, original_shape)
        
        return grad


def broadcast_arrays(a_shape, b_shape):
    return BroadcastInfo(a_shape, b_shape).result_shape


def check_broadcastable(a_shape, b_shape):
    try:
        info = BroadcastInfo(a_shape, b_shape)
        return True, info.result_shape
    except ValueError:
        return False, None
