# Tensor internals

## The problem a tensor has to solve

A dense tensor needs three things: somewhere to put the numbers, a shape, and
a way to reinterpret the layout without copying. The last one is where the
design decisions live.

## Storage, shape, stride

A `Tensor` is small: a shared storage pointer, a `Shape`, a stride tuple, an
offset, a dtype, and an optional graph node. Everything else is derived.

```python
tensor = Tensor(storage, Shape((2, 3)), stride=(3, 1), offset=0, dtype=float32)
```

`Storage` owns the buffer and is shared. Two tensors over the same storage
are two windows onto one array.

A row-major `(2, 3)` tensor has strides `(3, 1)`: element `(i, j)` sits at
flat index `i * 3 + j`. A transposed view keeps the same buffer but swaps the
dimensions *and* the strides, giving shape `(3, 2)` and strides `(1, 3)`. No
memory moves.

## Materializing a strided view

Reading a strided view back into a dense array uses `numpy.lib.stride_tricks.as_strided`
over a flat alias of the storage:

```python
flat = array.reshape(-1)                       # view, no copy
return as_strided(flat[offset:], shape, byte_strides)
```

Three details matter here, and each one was a bug first:

**The storage must be flattened first.** `array[offset:]` on a
multi-dimensional array slices the *first axis*, not the flat element offset.
Flattening is a view, so it costs nothing.

**The rank must come from `.ndim`, never `len()`.** `len()` on a NumPy array
is its first axis, not its dimension count. Using it to pad a batched
gradient silently inserts a leading singleton axis.

**The view is bounds-checked.** The minimum and maximum reachable offsets are
computed from the shape and stride and compared against the buffer size. An
empty view is exempt, because an empty slice legitimately starts at or past
the end.

## Views and gradients

A view shares memory, so a gradient computed for the view must be routed back
to the base tensor. Without a graph node for each view kind, a parameter that
only ever appears as `weight.transpose(0, 1)` — which is every `Linear` layer —
receives no gradient at all, and the model still trains, just badly.

Each view kind has a spec pairing the forward operation with its inverse:

| Spec | Forward | Inverse |
| --- | --- | --- |
| `TransposeSpec` | swap two axes | swap the same two axes of the gradient |
| `PermuteSpec` | reorder axes | apply the inverse permutation |
| `ReshapeSpec` | new shape, same elements | reshape back |
| `SqueezeSpec` / `UnsqueezeSpec` | add or drop size-1 axes | reshape back |
| `SliceSpec` | strided slice | scatter into a zero-filled buffer |

Every inverse works on **logical** axes. Reapplying the forward view to a
gradient would reinterpret memory in a layout the gradient does not have,
which scrambles values silently.

`SliceSpec` is the one inverse that is not a reshape. A slice moves elements,
so its inverse places the gradient at the positions the slice read from and
zeroes everything else. Integer indices select one position, so they scatter
into a length-1 window of their axis.

## Strided reshape needs a node

Reinterpreting a non-contiguous tensor's shape requires a physical copy, and a
copy made outside the graph would cut the connection to everything upstream.
`Materialize` is a Function whose backward is the identity, so the reshape
that follows attaches to it instead:

```python
def reshape(self, *shape):
    spec = ReshapeSpec(target, self._shape.dims)
    if self.is_contiguous:
        return self._make_view(spec)
    return Materialize.apply(self)._make_view(spec)
```

This sits on the attention hot path: heads are permuted and then reshaped on
the way into a matmul. Getting it wrong meant the entire attention sub-graph
received no gradient, which is why the attention gradients were wrong while the
feed-forward ones were correct.

## Broadcasting

Broadcasting is resolved once per call rather than per element. `prepare_broadcast`
returns the output shape, per-operand strides aligned to it, and the axes where
any operand is being reused.

A broadcast operand gets stride `0` on the expanded axis, so a kernel that
walks the output re-reads the same source element. NumPy does this in C; here
the strides are computed explicitly so the same machinery serves reductions,
which is where broadcasting most often causes errors.

Reductions need the inverse operation. `_reduce_batch` sums the axes a shared
weight was expanded over, and `_expand_reduced` re-inserts reduced axes as
singletons so ordinary broadcasting expands them back.

## dtypes

A `DType` is a value object with a promotion rule. Integers promote to floats,
low precision to high, and complex absorbs real. Reductions accumulate in a
wider type than their input: float16 in float32, integers in int64.

`tensor(...)` applies one default consistently. A Python float, a list of
floats, and a nested list of floats all become float32. Letting a plain list
fall through to NumPy's inference would make `tensor([1.0])` float64 while
`tensor(1.0)` is float32, which is the kind of inconsistency that only shows
up as a dtype error three layers away.

## Serialization

The on-disk format is a zip of two parts: a JSON manifest and raw little-endian
bytes per tensor.

```python
def serialize_tensor(t):
    dense = np.ascontiguousarray(t.numpy(), dtype=_little_endian(t.dtype).np_dtype)
    header = json.dumps({"dtype": ..., "shape": ..., "nbytes": ...}).encode()
    return MAGIC + struct.pack("<II", version, len(header)) + header + dense.tobytes()
```

Raw bytes rather than pickle, deliberately: a checkpoint loader that executes
code on load is a remote-code-execution path for anyone who can write a
checkpoint. Byte order is fixed to little-endian so a file written on one
machine reads identically on another.

`save_checkpoint` takes `extra_states` for tensors belonging to other modules.
Namespaced keys are split back out on load, so a language model can store its
head and its optimizer state in the same file as the encoder.

## Why not just use NumPy

NumPy is not a deep learning framework. It has no autodiff, no device
abstraction, no notion of a parameter, and no graph. Reimplementing `matmul`
would add risk without adding capability, because NumPy already dispatches to
optimized BLAS. The parts worth owning are the tensor abstraction, the view
and gradient semantics, the autodiff contract, and the module system, and those
are what this package implements.