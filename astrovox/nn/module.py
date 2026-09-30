"""Base class for all neural network modules.

The module system mirrors the familiar ``Module`` contract: parameters are
tensors, submodules are registered by assignment, ``forward`` is the only
required method, and traversal helpers cover the rest.
"""

from __future__ import annotations

from typing import Any, Callable, Iterator, Sequence

import numpy as np

from astrovox.tensor.dtype import DType
from astrovox.tensor.shape import Shape
from astrovox.tensor.tensor import Tensor


class Parameter(Tensor):
    """A tensor that is trained rather than computed.

    A parameter is a leaf: it always requires gradients and never carries a
    graph node, so an optimizer can update it in place.
    """

    __slots__ = ("name", "requires_grad", "_grad_fn", "_grad", "_version", "_storage", "_shape", "_stride", "_offset", "dtype", "device")

    def __init__(self, data: Tensor, name: str = "") -> None:
        super().__init__(
            data._storage,
            data.shape,
            data.stride,
            data._offset,
            data.dtype,
            data.device,
            requires_grad=True,
        )
        self.name = name
        self._grad_fn = None
        self._grad = None

    def __repr__(self) -> str:
        return f"Parameter containing:\n{str(self._to_dense())}"

    def __str__(self) -> str:
        return np.array2string(self._to_dense(), threshold=64, edgeitems=6)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-data description of this parameter."""
        return {"shape": list(self.shape.dims), "dtype": self.dtype.name, "numel": self.numel}


class Module:
    """Base class for neural network modules.

    Subclasses set parameters in ``__init__`` and implement ``forward``. Any
    attribute assigned an :class:`Module` or a sequence of them is registered
    as a child, so traversal, state dicts, and device moves work automatically.
    """

    def __init__(self) -> None:
        self._parameters: dict[str, Parameter] = {}
        self._buffers: dict[str, Tensor] = {}
        self._modules: dict[str, Module] = {}
        self._children: list[Module] = []
        self._hooks: dict[str, list[Callable[..., Any]]] = {}
        self.training: bool = True

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def __setattr__(self, name: str, value: Any) -> None:
        """Register parameters, buffers, and child modules on assignment."""
        if isinstance(value, Parameter):
            self._ensure_registry()._parameters[name] = value
        elif isinstance(value, Module):
            modules = self.__dict__.get("_modules")
            if modules is not None:
                modules[name] = value
            self.__dict__.setdefault("_children", []).append(value)
        object.__setattr__(self, name, value)

    def _ensure_registry(self) -> "Module":
        """Return self, creating the registries if construction is partial."""
        self.__dict__.setdefault("_parameters", {})
        self.__dict__.setdefault("_buffers", {})
        self.__dict__.setdefault("_modules", {})
        self.__dict__.setdefault("_children", [])
        self.__dict__.setdefault("_hooks", {})
        return self

    def register_parameter(self, name: str, param: Parameter | None) -> None:
        """Add or remove a named parameter."""
        if param is None:
            self._parameters.pop(name, None)
        else:
            self._parameters[name] = param

    def register_buffer(self, name: str, tensor: Tensor | None, persistent: bool = True) -> None:
        """Add or remove a named buffer.

        Non-persistent buffers are excluded from the state dict, which suits
        running statistics that are recomputed rather than trained.
        """
        if tensor is None:
            self._buffers.pop(name, None)
        else:
            self._buffers[name] = tensor
            if not persistent:
                self._non_persistent_buffers = getattr(self, "_non_persistent_buffers", set()) | {name}

    def register_module(self, name: str, module: Module | None) -> None:
        """Add or remove a named child module."""
        if module is None:
            self._modules.pop(name, None)
        else:
            self._modules[name] = module

    def add_module(self, name: str, module: Module) -> "Module":
        """Attach ``module`` as a child under ``name`` and return self."""
        setattr(self, name, module)
        return self

    def add_module_list(self, name: str, modules: Sequence[Module]) -> "Module":
        """Attach a sequence of modules as ``name.0``, ``name.1``, and so on."""
        holder = Sequential(*modules)
        setattr(self, name, holder)
        return self

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def named_parameters(self, prefix: str = "", recurse: bool = True) -> Iterator[tuple[str, Parameter]]:
        """Yield ``(name, parameter)`` pairs in a stable order."""
        for name, param in self._parameters.items():
            if param is not None:
                yield (f"{prefix}{name}", param)
        if recurse:
            for child_name, child in self._modules.items():
                yield from child.named_parameters(f"{prefix}{child_name}.")

    def parameters(self, recurse: bool = True) -> Iterator[Parameter]:
        """Yield every parameter, discarding names."""
        for _, param in self.named_parameters(recurse=recurse):
            yield param

    def named_buffers(self, prefix: str = "", recurse: bool = True) -> Iterator[tuple[str, Tensor]]:
        """Yield ``(name, buffer)`` pairs for persistent buffers."""
        non_persistent = getattr(self, "_non_persistent_buffers", set())
        for name, buf in self._buffers.items():
            if name not in non_persistent:
                yield (f"{prefix}{name}", buf)
        if recurse:
            for child_name, child in self._modules.items():
                yield from child.named_buffers(f"{prefix}{child_name}.", recurse)

    def named_modules(self, prefix: str = "", recurse: bool = True) -> Iterator[tuple[str, "Module"]]:
        """Yield ``(name, module)`` pairs including this module first."""
        yield (prefix.rstrip("."), self)
        if recurse:
            for name, child in self._modules.items():
                yield from child.named_modules(f"{prefix}{name}.", recurse)

    def modules(self) -> Iterator["Module"]:
        """Yield every submodule, discarding names."""
        for _, module in self.named_modules():
            yield module

    def children(self) -> Iterator["Module"]:
        """Yield the direct children of this module."""
        return iter(self._modules.values())

    # ------------------------------------------------------------------
    # Modes
    # ------------------------------------------------------------------

    def train(self, mode: bool = True) -> "Module":
        """Set this module and all children to training or evaluation mode."""
        self.training = mode
        for child in self._modules.values():
            child.train(mode)
        return self

    def eval(self) -> "Module":
        """Switch to evaluation mode and return self."""
        return self.train(False)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def state_dict(self, prefix: str = "") -> dict[str, Tensor]:
        """Return every parameter and persistent buffer keyed by name."""
        state: dict[str, Tensor] = {}
        for name, param in self._parameters.items():
            if param is not None:
                state[f"{prefix}{name}"] = param
        for name, buf in self.named_buffers(prefix):
            state[name] = buf
        for child_name, child in self._modules.items():
            state.update(child.state_dict(f"{prefix}{child_name}."))
        return state

    def load_state_dict(self, state: dict[str, Tensor], strict: bool = True) -> tuple[list[str], list[str]]:
        """Load parameters from ``state``; returns ``(missing, unexpected)``."""
        own = dict(self.named_parameters())
        own.update(dict(self.named_buffers()))

        missing = [name for name in own if name not in state]
        unexpected = [name for name in state if name not in own]
        if strict and (missing or unexpected):
            raise RuntimeError(
                f"State dict mismatch. Missing keys: {missing}. Unexpected keys: {unexpected}"
            )

        for name, target in own.items():
            source = state.get(name)
            if source is None:
                continue
            if source.shape != target.shape:
                if strict:
                    raise RuntimeError(
                        f"Shape mismatch for {name}: checkpoint has {tuple(source.shape.dims)}, "
                        f"module expects {tuple(target.shape.dims)}"
                    )
                continue
            # Copy through the existing buffer so views onto the parameter stay valid.
            target.numpy()[...] = source.numpy()
        return missing, unexpected

    def zero_grad(self, set_to_none: bool = True) -> None:
        """Clear gradients on every parameter."""
        for param in self.parameters():
            if set_to_none:
                param._grad = None
            elif param._grad is not None:
                param._grad = param._grad * 0.0

    def num_parameters(self, trainable_only: bool = True) -> int:
        """Return the total parameter count."""
        total = 0
        for param in self.parameters():
            if not trainable_only or param.requires_grad:
                total += param.numel
        return total

    def parameter_summary(self) -> str:
        """Return a human-readable parameter breakdown."""
        rows = [f"{'name':<40} {'shape':<20} {'params':>10}"]
        total = 0
        for name, param in self.named_parameters():
            rows.append(f"{name:<40} {str(tuple(param.shape.dims)):<20} {param.numel:>10,}")
            total += param.numel
        rows.append(f"{'TOTAL':<40} {'':<20} {total:>10,}")
        return "\n".join(rows)

    # ------------------------------------------------------------------
    # Device and dtype
    # ------------------------------------------------------------------

    def to_device(self, device: Any) -> "Module":
        """Move every parameter and buffer to ``device`` in place."""
        for param in self.parameters():
            moved = param.to(device)
            param._storage = moved._storage
            param._shape = moved._shape
            param._stride = moved._stride
            param._offset = moved._offset
            param.device = device
        for name, buf in list(self._buffers.items()):
            self._buffers[name] = buf.to(device)
        return self

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def register_forward_hook(self, hook: Callable[..., Any]) -> Callable[[], None]:
        """Register a hook called as ``hook(module, inputs, output)``."""
        self._ensure_registry()._hooks.setdefault("forward", []).append(hook)

        def remove() -> None:
            self._hooks["forward"].remove(hook)

        return remove

    def register_backward_hook(self, hook: Callable[..., Any]) -> Callable[[], None]:
        """Register a hook called as ``hook(module, grad_output)``."""
        self._ensure_registry()._hooks.setdefault("backward", []).append(hook)

        def remove() -> None:
            self._hooks["backward"].remove(hook)

        return remove

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        """Compute this module's output. Must be implemented by subclasses."""
        raise NotImplementedError(f"{type(self).__name__} must implement forward()")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Run :meth:`forward`, firing any registered hooks."""
        inputs = (args, kwargs)
        result = self.forward(*args, **kwargs)
        for hook in self._hooks.get("forward", []):
            result = hook(self, inputs, result) or result
        return result

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.parameter_summary().splitlines()[-1].strip()})"


class FunctionalModule(Module):
    """A module wrapping a plain function, for quick composition."""

    def __init__(self, fn: Callable[..., Tensor], name: str = "fn") -> None:
        super().__init__()
        self.fn = fn
        self._label = name

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        """Apply the wrapped function."""
        return self.fn(*args, **kwargs)


class ModuleList(Module):
    """An ordered container of child modules indexed by position."""

    def __init__(self, modules: Sequence[Module] | None = None) -> None:
        super().__init__()
        self._list: list[Module] = []
        for i, module in enumerate(modules or []):
            self.add_module(str(i), module)

    def add_module(self, name: str, module: Module) -> "Module":  # type: ignore[override]
        """Append ``module`` under an explicit key."""
        self._list.append(module)
        self._modules[name] = module
        return self

    def __len__(self) -> int:
        return len(self._list)

    def __iter__(self) -> Iterator[Module]:
        return iter(self._list)

    def __getitem__(self, index: int) -> Module:
        return self._list[index]

    def forward(self, *args: Any, **kwargs: Any) -> Any:
        """Not meaningful for a container; iterate the children instead."""
        raise NotImplementedError("ModuleList is a container, not a function")


# ----------------------------------------------------------------------
# Parameter initialization
# ----------------------------------------------------------------------


def parameter(data: np.ndarray | Tensor, name: str = "", requires_grad: bool = True) -> Parameter:
    """Wrap array data as a trainable :class:`Parameter`."""
    t = data if isinstance(data, Tensor) else Tensor.from_numpy(np.asarray(data))
    param = Parameter(t, name=name)
    param.requires_grad_(requires_grad)
    return param


def init_uniform(param: Parameter, bound: float = 0.0) -> Parameter:
    """Initialize from a uniform distribution in ``[-bound, bound]``."""
    rng = np.random.default_rng()
    param.numpy()[...] = rng.uniform(-bound, bound, param.shape.dims).astype(param.dtype.np_dtype)
    return param


def init_normal(param: Parameter, mean: float = 0.0, std: float = 0.02) -> Parameter:
    """Initialize from a normal distribution."""
    rng = np.random.default_rng()
    param.numpy()[...] = rng.normal(mean, std, param.shape.dims).astype(param.dtype.np_dtype)
    return param


def init_xavier_uniform(param: Parameter, gain: float = 1.0) -> Parameter:
    """Xavier/Glorot uniform initialization, the default for dense layers."""
    fan_in, fan_out = _fan_in_out(param.shape.dims)
    limit = gain * np.sqrt(6.0 / (fan_in + fan_out))
    return init_uniform(param, limit)


def init_xavier_normal(param: Parameter, gain: float = 1.0) -> Parameter:
    """Xavier/Glorot normal initialization."""
    fan_in, fan_out = _fan_in_out(param.shape.dims)
    std = gain * np.sqrt(2.0 / (fan_in + fan_out))
    return init_normal(param, 0.0, std)


def init_kaiming_uniform(param: Parameter, mode: str = "fan_in", gain: float = 1.0) -> Parameter:
    """He initialization for rectified activations."""
    fan_in, fan_out = _fan_in_out(param.shape.dims)
    fan = fan_in if mode == "fan_in" else fan_out
    limit = gain * np.sqrt(3.0 / fan)
    return init_uniform(param, limit)


def init_kaiming_normal(param: Parameter, mode: str = "fan_in", gain: float = 1.0) -> Parameter:
    """He normal initialization for rectified activations."""
    fan_in, fan_out = _fan_in_out(param.shape.dims)
    fan = fan_in if mode == "fan_in" else fan_out
    return init_normal(param, 0.0, gain * np.sqrt(2.0 / fan))


def init_orthogonal(param: Parameter, gain: float = 1.0) -> Parameter:
    """Orthogonal initialization, which preserves variance through deep stacks."""
    flat = param.numpy().reshape(param.shape.dims[-2], -1)
    rows, cols = flat.shape
    rng = np.random.default_rng()
    matrix = rng.standard_normal((rows, cols))
    u, _, vt = np.linalg.svd(matrix, full_matrices=False)
    if rows < cols:
        result = u
    else:
        result = vt.T
    param.numpy()[...] = (gain * result).reshape(param.shape.dims)
    return param


def init_zeros(param: Parameter) -> Parameter:
    """Initialize to zero, used for residual-branch outputs."""
    param.zero_()
    return param


def init_ones(param: Parameter) -> Parameter:
    """Initialize to one, used for normalization scales and residual gains."""
    param.fill_(1.0)
    return param


def _fan_in_out(shape: Sequence[int]) -> tuple[int, int]:
    """Return ``(fan_in, fan_out)`` for a weight tensor."""
    if len(shape) < 2:
        return 1, max(1, shape[0] if shape else 1)
    receptive = int(np.prod(shape[2:])) if len(shape) > 2 else 1
    fan_in = shape[-2] * receptive
    fan_out = shape[-1] * receptive
    return fan_in, fan_out


def get_submodule(module: Module, path: str) -> Module:
    """Return the submodule at a dotted ``path``.

    Raises:
        KeyError: if any component of the path is missing.
    """
    current: Module = module
    for part in path.split("."):
        if part not in current._modules:
            raise KeyError(f"No submodule named {part!r} in {type(current).__name__}")
        current = current._modules[part]
    return current


class Sequential(Module):
    """A chain of modules applied in order.

    Defined here rather than in ``sequential.py`` so that the module system has
    no import cycle; that module re-exports it alongside extra containers.
    """

    def __init__(self, *modules: Module) -> None:
        super().__init__()
        self._ordered: list[Module] = []
        for i, module in enumerate(modules):
            self.add_module(str(i), module)

    def add_module(self, name: str, module: Module) -> "Sequential":  # type: ignore[override]
        """Append ``module`` to the end of the chain."""
        self._ordered.append(module)
        self._modules[name] = module
        return self

    def append(self, module: Module) -> "Sequential":
        """Append ``module`` with the next positional key."""
        return self.add_module(str(len(self._ordered)), module)

    def __len__(self) -> int:
        return len(self._ordered)

    def __iter__(self) -> Iterator[Module]:
        return iter(self._ordered)

    def __getitem__(self, index: int) -> Module:
        return self._ordered[index]

    def forward(self, x: Any) -> Any:
        """Pass ``x`` through every module in order."""
        for module in self._ordered:
            x = module(x)
        return x

    def __repr__(self) -> str:
        body = "\n".join(f"  ({i}): {m}" for i, m in enumerate(self._ordered))
        return f"Sequential(\n{body}\n)" if body else "Sequential()"
