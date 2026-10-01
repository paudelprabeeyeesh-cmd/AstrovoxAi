# Autograd design

## Shape of the problem

Reverse-mode autodiff for a deep network has to answer three questions:

1. How does a tensor remember what produced it?
2. What order do the backward functions run in?
3. When several operations read the same tensor, how do their gradients add?

The hard part is not any single answer but keeping the contract narrow enough
that all three stay consistent. Most of the bugs found during development came
from the contract being loose in one place and relied upon in another.

## The graph

A `Function` implements `forward(ctx, *args)` and `backward(ctx, grad)`.
`apply` calls forward, and if recording is enabled and any input requires a
gradient, builds a `GraphNode` and attaches it to the result:

```python
def apply(cls, *args, **kwargs):
    ctx = _FunctionContext()
    result = cls.forward(ctx, *args, **kwargs)
    if graph.is_enabled() and cls._requires_grad(args, result):
        node = GraphNode(cls, ctx, tuple(args), outputs)
        for output in outputs:
            set_tensor_grad_fn(output, node)
    return result
```

The graph is implicit. Tensors carry a pointer to the node that produced them;
nodes carry their inputs and pointers to those inputs' producers. Building it
costs one pointer per operation and needs no separate topologically sorted
structure.

`ctx` holds what forward saved for backward — the softmax output a Jacobian
needs, a reshaped input, a mask. Saving less means recomputing; saving more
means holding memory for nothing, which `validate_backward` will point out.

## The backward contract

Two rules, both learned the hard way.

**Always return a tuple.** One gradient per forward input, positionally.
Returning a bare tensor for a single-input operation makes the engine iterate
that tensor's *rows* and treat each as a separate input gradient. For a `(5, 6)`
gradient that produces five gradients of shape `(6,)` instead of one of `(5, 6)`.
The result looks plausible — a loss still falls — while every layer before the
operation is silently dead.

**`None` means skip.** Returning `None` for an input marks it as not needing a
gradient, which lets the engine avoid computing it.

```python
class ReLU(Function):
    @staticmethod
    def forward(ctx, x):
        ctx.save(x=x)
        return Tensor.from_numpy(np.maximum(x.numpy(), 0), ...).requires_grad_(x.requires_grad)

    @staticmethod
    def backward(ctx, grad_output):
        return (grad_output * (ctx.load("x").numpy() > 0),)   # a tuple
```

The engine also normalizes a bare tensor to a one-element tuple, so a
sloppy backward degrades to "only works on scalars" rather than to "silently
wrong". That is a deliberate safety net under a documented contract.

## Ordering

Nodes record a monotonically increasing sequence number when created. Sorting
descending by that number gives a valid evaluation order for free: every
producer is created before its consumers, so every consumer has a higher number
and is visited first.

```python
nodes = sorted(walk_from(roots), key=lambda n: n.sequence_nr, reverse=True)
```

`walk_from` marks nodes seen by identity, so a shared subgraph — a weight used
by three layers — is expanded once.

## Accumulation

A tensor read by several consumers receives several gradients, and they must
sum. The engine collects them into `incoming[node_id]` and combines when the
node is visited:

```python
grad_output = contributions[0] if len(contributions) == 1 else _sum_tensors(contributions)
```

Leaves are different: their gradient accumulates on the tensor itself, so
calling backward twice without clearing doubles the gradient. That is what
makes gradient accumulation across micro-batches work, and it is why
`optimizer.zero_grad()` appears once per step.

## Aligning gradients

A node's backward receives a gradient shaped like its own output, and returns
one gradient per input, shaped so it broadcasts against that input.

The subtlety is *which* shape. The gradient at position `i` belongs to
`node.inputs[i]` — the current node's input, not the parent's. Indexing the
parent's input list with the current node's position silently puts the gradient
on the wrong operand whenever the two differ, which is exactly the case for any
node downstream of a view.

```python
source = node.inputs[position]
parent, _ = node.next_functions[position]
if parent is None:
    source._grad = grad if source._grad is None else source._grad + grad
else:
    incoming[id(parent)].append(_broadcast_like(grad, source))
```

Alignment is by broadcasting, not reshaping, because a reduction legitimately
hands a scalar down and a broadcast scalar is correct for any shape.

## Broadcast and reduction inverses

An operand expanded from extent 1 receives a gradient with the broadcast
shape, and those axes must be summed away:

```python
def unbroadcast(grad, target):
    if grad.shape == target:
        return grad
    if is_broadcastable(grad.shape, target):
        return grad      # a reduction passed a scalar down; it already broadcasts
    axes = set(range(max(grad.ndim - target.ndim, 0)))
    axes.update(axis for axis, dim in enumerate(target.dims) if dim == 1)
    if axes:
        grad = _sum_dims(grad, tuple(sorted(axes)))
    return grad.reshape(target)
```

The middle case is the one that is easy to miss. A full reduction returns a
scalar, which already broadcasts; summing and reshaping it against a `(1, 2)`
target fails because there are not enough elements.

Reductions go the other way. `_expand_reduced` re-inserts reduced axes as
singletons so broadcasting expands them, which handles a partial reduction
uniformly:

```python
if not axes or grad.shape == target or len(axes) >= target.ndim:
    return grad
dims = [1 if axis in axes else dim for axis, dim in enumerate(target.dims)]
return grad.reshape(Shape(dims))
```

## Batched matmul

`d(a) = grad . bᵀ` and `d(b) = aᵀ . grad`, and a weight shared across a batch
has its gradient summed over the batch axes. Getting this wrong leaves a weight
gradient carrying a spurious leading dimension, which fails shape validation
rather than producing plausible numbers.

A vector operand contracts against a different axis than a matrix does, so the
two cases are written separately with `einsum`, which states which axes are
summed instead of relying on rank rules that do not line up when a rank is
missing:

```python
if b_was_vector:
    grad_a = np.einsum("...n,k->...nk", grad, b_matrix).reshape(a.shape.dims)
    grad_b = np.einsum("...nk,...n->k", a_matrix, grad)
```

## Views are graph nodes

The rule that cost the most to learn: **a view must record a node, or its
gradient stops at the view.** `Linear` computes `x @ weight.T`, so the weight
only ever appears in the graph as a transpose view. With no node there, the
weight receives no gradient and the model trains its last layer only.

Each view spec pairs the forward operation with its inverse, and the inverse
works on logical axes rather than memory. Slices invert by scattering into a
zero-filled buffer. A strided reshape copies through `Materialize`, whose
backward is the identity, so the copy does not cut the graph.

## no_grad

Graph recording is thread-local and off with `no_grad`, usable as a context
manager or a decorator:

```python
with no_grad():
    logits = model(x)        # no nodes allocated, no backward path
```

`@no_grad()` on `evaluate` is what keeps validation from building a graph it
would only discard.

## Verifying it

Three independent checks, because they fail differently:

**Closed form.** Tiny graphs of two to five operations, each derivative
derived by hand. `d(sqrt(t)) = 1/(2 sqrt(t))`, `d(a²-b²)/da = 2a`. A mistake in
the engine cannot hide behind a matching mistake in the reference.

**Directional derivative.** For matmul, `<grad, d(input)> == <seed, d(output)>`.
This depends only on the forward pass, so it stays valid for batched shapes
where a flattened reference does not.

**Numerical difference.** Central differences against the analytic gradient.
The criterion is on norms, not per element:

```
||analytical - numerical|| <= atol + rtol * max(||analytical||, ||numerical||)
```

A per-element relative test is undefined where the true gradient is near zero,
which in float32 differencing is just noise. In float32 the default `eps` is
1e-3; a smaller step measures rounding rather than the derivative.

Two situations need explicit handling rather than a tolerance:

- **Non-smooth functions.** A finite difference across a ReLU kink straddles
  the corner and reports roughly zero. Check ReLU with inputs held clear of
  zero, and use a smooth activation when sweeping depths.
- **Genuinely zero gradients.** An attention key bias has an exactly zero
  gradient because softmax is invariant to a per-row shift. That is a
  property, not a bug, and there is a test saying so.

## Higher-order gradients

Not implemented. The engine's contract does not support it: a backward
returning tensors that themselves require gradients would need their own graph
nodes, which `apply` does not create. A second-order implementation would
either retrace the backward graph or introduce a dual-number type.