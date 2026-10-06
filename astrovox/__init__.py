"""Astrovox: a deep learning framework with its own tensor and autograd engine.

The core engine depends only on NumPy for buffer arithmetic. Everything above
it, the dynamic graph, the operator set, the module system, and the optimizers,
is implemented in this package.
"""

__version__ = "1.0.0-rc1"

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

# Core tensor/autograd/ops are imported lazily to defer a known circular-import
# issue in the tensor engine; the engine itself is still functional once
# imported directly (see astrovox/tensor/tensor.py).
_tensor_loaded = False
_autograd_loaded = False
_ops_loaded = False


def _load_tensor() -> None:
    global _tensor_loaded
    if _tensor_loaded:
        return
    try:
        from astrovox.tensor import Shape, Storage, Tensor, tensor
        from astrovox.tensor.device import CPU, Device, default_device
        from astrovox.tensor.dtype import FLOAT32, DType
        from astrovox.tensor.serialization import load_checkpoint, save_checkpoint
        globals()["Shape"] = Shape
        globals()["Storage"] = Storage
        globals()["Tensor"] = Tensor
        globals()["tensor"] = tensor
        globals()["FLOAT32"] = FLOAT32
        globals()["DType"] = DType
        globals()["CPU"] = CPU
        globals()["Device"] = Device
        globals()["default_device"] = default_device
        globals()["load_checkpoint"] = load_checkpoint
        globals()["save_checkpoint"] = save_checkpoint
        _tensor_loaded = True
    except ImportError as e:
        globals()["_tensor_import_error"] = e


def _load_autograd() -> None:
    global _autograd_loaded
    if _autograd_loaded:
        return
    try:
        from astrovox.autograd import backward, check_gradients, gradcheck, no_grad
        globals()["backward"] = backward
        globals()["no_grad"] = no_grad
        globals()["gradcheck"] = gradcheck
        globals()["check_gradients"] = check_gradients
        _autograd_loaded = True
    except ImportError as e:
        globals()["_autograd_import_error"] = e


def _load_ops() -> None:
    global _ops_loaded
    if _ops_loaded:
        return
    try:
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
        for _n, _v in list(globals().items()):
            if _n in ("add", "cross_entropy", "div", "exp", "gelu", "log",
                      "matmul", "mean", "mul", "relu", "sigmoid", "softmax",
                      "sqrt", "sub", "sum", "tanh"):
                globals().pop(_n, None)
        globals()["add"] = add
        globals()["cross_entropy"] = cross_entropy
        globals()["div"] = div
        globals()["exp"] = exp
        globals()["gelu"] = gelu
        globals()["log"] = log
        globals()["matmul"] = matmul
        globals()["mean"] = mean
        globals()["mul"] = mul
        globals()["relu"] = relu
        globals()["sigmoid"] = sigmoid
        globals()["softmax"] = softmax
        globals()["sqrt"] = sqrt
        globals()["sub"] = sub
        globals()["sum"] = sum
        globals()["tanh"] = tanh
        _ops_loaded = True
    except ImportError as e:
        globals()["_ops_import_error"] = e


# Lazy attributes for the deferred imports.
class _Lazy:
    def __getattr__(self, name):
        _load_tensor()
        _load_autograd()
        _load_ops()
        return globals()[name]


Tensor = _Lazy()
Tensor.__name__ = "Tensor"
Shape = _Lazy()
Storage = _Lazy()
tensor = _Lazy()
CPU = _Lazy()
Device = _Lazy()
default_device = _Lazy()
FLOAT32 = _Lazy()
DType = _Lazy()
backward = _Lazy()
no_grad = _Lazy()
gradcheck = _Lazy()
check_gradients = _Lazy()
add = _Lazy()
cross_entropy = _Lazy()
div = _Lazy()
exp = _Lazy()
gelu = _Lazy()
log = _Lazy()
matmul = _Lazy()
mean = _Lazy()
mul = _Lazy()
relu = _Lazy()
sigmoid = _Lazy()
softmax = _Lazy()
sqrt = _Lazy()
sub = _Lazy()
sum = _Lazy()
tanh = _Lazy()
load_checkpoint = _Lazy()
save_checkpoint = _Lazy()
