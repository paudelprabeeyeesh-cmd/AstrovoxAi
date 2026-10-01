"""Throwaway: trace gradient accumulation through the engine."""

import numpy as np

from astrovox import tensor
from astrovox.nn import Linear, ReLU, Sequential
from astrovox.ops import cross_entropy
from astrovox.autograd.engine import Engine, _broadcast_like

rng = np.random.default_rng(0)
model = Sequential(Linear(4, 6), ReLU(), Linear(6, 3))
x = tensor(rng.standard_normal((5, 4)).astype(np.float32))
y = tensor(np.array([0, 1, 2, 0, 1]))
loss = cross_entropy(model(x), y)

import astrovox.autograd.engine as eng

trace = []
orig_run = Engine._run_node if hasattr(Engine, "_run_node") else None

# Wrap backward calls to see what each node receives and emits.
from astrovox.autograd.graph import walk_from

nodes = sorted(walk_from([loss]), key=lambda n: n.sequence_nr, reverse=True)
for n in nodes:
    trace.append((n.sequence_nr, n.name))

print("order:", trace)

# Replicate the engine loop with logging.
from collections import defaultdict

seeds = [eng.ones_like(loss)]
incoming = defaultdict(list)
incoming[id(loss._grad_fn)].append(seeds[0])

leaves = {}
for node in nodes:
    contributions = incoming.get(id(node))
    print(f"\n--- node {node.sequence_nr} {node.name}: contributions={len(contributions) if contributions else 0}")
    if not contributions:
        continue
    grad_output = contributions[0] if len(contributions) == 1 else contributions[0]
    grad_output = eng._align_to_outputs(node, grad_output)
    print(f"    grad_output shape {tuple(grad_output.shape.dims)} absmax {abs(grad_output.numpy()).max():.6g}")
    grads = node.function.backward(node.ctx, grad_output)
    if grads is None:
        print("    NO GRADS")
        continue
    for position, grad in enumerate(grads):
        if grad is None:
            continue
        source = node.inputs[position]
        parent, _ = node.next_functions[position]
        shp = tuple(source.shape.dims) if hasattr(source, "shape") else None
        gshp = tuple(grad.shape.dims)
        amax = abs(grad.numpy()).max() if grad.size else 0.0
        print(
            f"    pos{position} grad{ gshp} absmax {amax:.6g} -> source{shp} "
            f"parent={parent.name if parent else None}"
        )
        if parent is None:
            if hasattr(source, "requires_grad") and source.requires_grad:
                source._grad = grad
                leaves[id(source)] = source
        else:
            incoming[id(parent)].append(_broadcast_like(grad, source))

print("\nleaves with grad:", len(leaves))
for name, p in model.named_parameters():
    g = p.grad
    print(name, "None" if g is None else f"absmax {abs(g.numpy()).max():.6g}")
