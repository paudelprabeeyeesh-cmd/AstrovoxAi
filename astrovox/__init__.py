"""Astrovox: a deep learning framework with its own tensor and autograd engine.

The core engine depends only on NumPy for buffer arithmetic. Everything above
it, the dynamic graph, the operator set, the module system, and the optimizers,
is implemented in this package.
"""

from astrovox.tensor import Shape, Storage, Tensor, tensor
from astrovox.tensor.dtype import FLOAT32, DType
from astrovox.tensor.device import CPU, Device, default_device
from astrovox.tensor.serialization import load_checkpoint, save_checkpoint
from astrovox.autograd import backward, no_grad, gradcheck, check_gradients
from astrovox.ops import (
    add,
    cross_entropy,
    div,
    exp,
    gelu,
    log,
    matmul,
    mean,
    mul,
    relu,
    sigmoid,
    softmax,
    sqrt,
    sub,
    sum,
    tanh,
)

__version__ = "0.1.0"

__all__ = [
    "CPU",
    "DType",
    "Device",
    "FLOAT32",
    "Shape",
    "Storage",
    "Tensor",
    "__version__",
    "add",
    "backward",
    "check_gradients",
    "cross_entropy",
    "default_device",
    "div",
    "exp",
    "gelu",
    "gradcheck",
    "load_checkpoint",
    "log",
    "matmul",
    "mean",
    "mul",
    "no_grad",
    "relu",
    "save_checkpoint",
    "sigmoid",
    "softmax",
    "sqrt",
    "sub",
    "sum",
    "tanh",
    "tensor",
]
