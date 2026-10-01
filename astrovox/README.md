# Astrovox

A deep learning framework whose tensor engine and autodiff system are
implemented here rather than delegated. NumPy is used only as the buffer
arithmetic substrate: the tensor type, dynamic graph, reverse-mode
differentiation, operator set, module system, optimizers, debugger, and
profiler are all part of this package.

The core has no PyTorch dependency.

## Status

| Area | State |
| --- | --- |
| Tensor, broadcasting, strided views | Working, cross-checked against NumPy |
| Reverse-mode autodiff | Working; every layer of a 100-layer stack receives a gradient |
| Modules, optimizers, schedules | Working |
| Transformer with grouped-query attention | Working, trains end to end |
| Graph inspector and diagnostics | Working |
| Profiler and FLOP accounting | Working |
| Checkpoint, save and resume | Working, reproduces a step exactly |

887 tests pass across the repository, 223 of them for this package.

## Quick start

```python
import numpy as np
from astrovox import tensor
from astrovox.nn import Sequential, Linear, ReLU
from astrovox.ops import cross_entropy
from astrovox.autograd import backward
from astrovox.optim import AdamW

model = Sequential(Linear(4, 32), ReLU(), Linear(32, 2))
optimizer = AdamW(list(model.parameters()), lr=0.01)

x = tensor(np.random.default_rng(0).standard_normal((32, 4)).astype(np.float32))
y = tensor(np.random.default_rng(1).integers(0, 2, 32).astype(np.int64))

for _ in range(100):
    optimizer.zero_grad()
    loss = cross_entropy(model(x), y)
    loss.backward()          # or backward(loss)
    optimizer.step()
```

## What a training loop looks like

There is no `model.train()` / `model.eval()` requirement for the dense
layers, and no explicit device placement on a CPU-only host. The loop is
four calls:

1. `optimizer.zero_grad()` clears accumulated gradients.
2. `cross_entropy(model(x), y)` builds the graph and returns a scalar.
3. `loss.backward()` differentiates and accumulates into every reachable leaf.
4. `optimizer.step()` updates parameters.

Gradients accumulate, so running backward several times before a step sums
them. That is what makes gradient accumulation across micro-batches work
without any special mode.

## Layout

```
astrovox/
  tensor/      Shape, dtype, device, storage, the Tensor type, serialization
  autograd/    Function protocol, graph, reverse-mode engine, gradient checks
  ops/         Arithmetic, reductions, activations, normalization, losses, views
  nn/          Module base, layers, transformer
  optim/       SGD, Adam, AdamW, Lion, learning-rate schedules
  debug/       Graph inspector and the autograd diagnostics
  profile/     FLOP counting, profiler, allocation tracker
  nlp/         Tokenizers, datasets, the small language model
  tests/       223 tests
  docs/        Design notes
```

## Design notes

- [Tensor internals](docs/tensor.md) — storage, strides, views, broadcasting
- [Autograd design](docs/autograd.md) — the graph, the engine, the contract
- [Debugging](docs/debugging.md) — how to find a gradient that stops early
- [Execution and performance](docs/execution.md) — FLOPs, memory, the profiler

## Design decisions

**NumPy for buffers, everything else written here.** NumPy is a well-tested
array library, not a deep learning framework. Reimplementing `matmul` would
add risk without adding capability, whereas the parts that define a framework
— the tensor abstraction, view semantics, the autodiff contract, the module
system — are exactly the parts worth owning.

**Views share storage and their gradients route back.** A transpose or reshape
allocates no memory, which means its gradient must reach the base tensor
through a graph node or a parameter silently stops training. This was the
single largest source of bugs during development.

**Gradients are handled in logical order.** A view's inverse transposes the
gradient's axes directly rather than reinterpreting a strided buffer.
Reapplying the forward view to a gradient assumes a memory layout the gradient
does not have.

**The backward contract is explicit.** A `backward` returns one gradient per
forward input, always as a tuple. Returning a bare tensor makes the engine
iterate its rows, which looks like it works and silently computes the wrong
thing.

**Optimizer state is keyed by position, not identity.** An object id is only
meaningful inside one process, so keying state on it makes a checkpoint
unusable after reloading.

## Limitations

Honest about what is not here yet:

- CPU only. The `Device` abstraction and a backend registry exist, and a
  backend that implements `dispatch` will execute kernels, but there is no
  CUDA, ROCm, or Metal backend.
- Single-process. There is no gradient synchronization or checkpoint sharding
  across nodes.
- The compiler, compiler IR, operator fusion, and ahead-of-time compilation
  are not implemented. The profiler's FLOP accounting is the measurement layer
  that a compiler would build on.
- Attention materializes the full score matrix, so memory grows quadratically
  with sequence length. There is no paged or flash-attention kernel.
- Performance is NumPy-bound. A 100k-parameter transformer trains at roughly
  7 steps per second on CPU. Correctness is established; speed is not tuned.