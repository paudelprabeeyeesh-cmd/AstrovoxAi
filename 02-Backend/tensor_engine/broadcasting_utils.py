import numpy as np
from .broadcast import BroadcastInfo, check_broadcastable


def broadcast_shape(a_shape, b_shape):
    _, result = check_broadcastable(a_shape, b_shape)
    if result is None:
        raise ValueError(f"Cannot broadcast shapes {a_shape} and {b_shape}")
    return result


def expand_to(arr, shape):
    arr = np.asarray(arr)
    if arr.shape == shape:
        return arr
    if not check_broadcastable(arr.shape, shape)[0]:
        raise ValueError(f"Cannot broadcast {arr.shape} to {shape}")
    return np.broadcast_to(arr, shape)


def is_broadcastable(a_shape, b_shape):
    return check_broadcastable(a_shape, b_shape)[0]


def broadcast_to_shape(arr, shape):
    return expand_to(arr, shape)


def reduce_gradient(grad, original_shape):
    return BroadcastInfo(original_shape, grad.shape).reduce_gradient(grad, original_shape)
