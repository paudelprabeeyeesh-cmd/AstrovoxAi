# Debugging a graph

The failures worth catching here all look like success. A gradient that stops
early still lowers the loss. A parameter that never updates still reports a
decreasing curve. A backward that reshapes wrongly still produces numbers.

`astrovox.debug` exists to make those loud.

## Start with check_graph

```python
from astrovox.debug import check_graph

loss = cross_entropy(model(x), y)
problems = check_graph(loss, model)
```

Call it **before** `backward`. A backward releases the graph unless it was
retained, and reporting everything as disconnected afterwards would be worse
than saying nothing.

Before backward it reports parameters not connected to the graph. After — with
`retain_graph=True` — it reports parameters that received no gradient and
gradients containing NaN or infinity.

A parameter reaches the graph through a view, typically a transpose of a
weight, so connectivity is decided by **storage identity**, not object
identity. Checking `id(param)` would report every `Linear` weight as
disconnected.

## The dashboard

```python
from astrovox.debug import dashboard, gradient_consistency

report = dashboard(loss, model, checks=gradient_consistency(lambda: cross_entropy(model(x), y), model))
print(report.render())
```

```
=============================================================
                   ASTROVOX AUTOGRAD REPORT
=============================================================
Graph Nodes         : 12
Trainable Params    : 6
Longest Chain       : 9 ops

Gradient Check
-------------------------------------------------------------
Passed             : 6
Failed             : 0

Dead Parameters    : 0
Zero Gradients     : 0
NaN Gradients      : 0

Memory
-------------------------------------------------------------
Peak Memory        : 0.02 MB
Saved Tensors      : 19

Overall Status
-------------------------------------------------------------
HEALTHY
=============================================================
```

`dashboard` retains the graph so structural facts and gradient facts can be
reported together. A plain backward would leave the node count and chain depth
empty, and the report would look healthy for the wrong reason.

## Verifying gradients are right, not just present

A zero gradient is obvious. A *wrong* one is not.

```python
checks = gradient_consistency(loss_fn, model)
print(format_consistency(checks))
```

```
parameter                                   status     rel error    grad norm
--------------------------------------------------------------------
0.weight                                    PASS       4.452e-05      0.97221
0.bias                                      PASS       8.397e-05      0.34013
2.weight                                    PASS       1.093e-04      0.31019
2.bias                                      PASS       3.130e-04     0.092556
```

The reported error is `max_abs_error / ||analytical||`, a norm ratio. The
per-element relative error is not reported because it approaches 1 wherever the
true gradient is near zero, which reads like a failure when nothing is wrong.

The default threshold is 1e-3, suited to float32. Tightening it below the
rounding noise of a central difference measures the noise.

## Tracing where the backward stops

```python
print(propagation_trace(loss))
```

```
forward graph (first recorded to last):
|-- view #1099
|-- matmul #1100
|-- add #1101
|-- relu #1102
|-- view #1103
|-- matmul #1104
|-- add #1105
`-- cross_entropy #1107

backward order (root first):
    1. [ok] cross_entropy #1107
    2. [ok] add #1105
    3. [ok] matmul #1104
    4. [ok] view #1103
    5. [ok] relu #1102
    6. [ok] add #1101
    7. [ok] matmul #1100
    8. [ok] view #1099
  reached 8 of 8 recorded operations
```

The count at the end is the useful part. A backward that stops early lists
fewer operations than the forward recorded, and the last entry it reaches is
exactly where the graph was cut.

## Checking parameters actually moved

```python
before = model.state_dict()
optimizer.step()
print(format_updates(verify_updates(model, before)))
```

```
parameter                                   updated          delta  detail
------------------------------------------------------------------
0.weight                                    yes                  4
0.bias                                      yes                  2
2.weight                                    yes               7.73
```

A parameter that did not move gets a reason: no gradient was computed, the
gradient is exactly zero, or the gradient was nonzero but the step did not act
on it. That last case means a learning rate of zero, which is otherwise
invisible.

`state_dict` returns copies specifically so this snapshot survives the step
that follows it.

## Gradient distribution

Norms hide shape. A gradient can have a healthy norm while being entirely NaN,
or entirely one value.

```python
print(format_distribution(gradient_distribution(model)))
```

```
parameter                                min       max      mean       std         l2   zero%   nan%   inf%
---------------------------------------------------------------------------------------------------
0.weight                             -0.7583     0.516  -0.00853    0.2315       1.31     0.0    0.0    0.0
```

The `zero%` column catches a dead layer that a norm would not: a gradient of
the right magnitude concentrated on a few elements reads as healthy.

## Shape validation

```python
problems = validate_shapes(loss)
```

Every gradient is checked against the operand it belongs to. A mismatch is the
signature of a backward that reshapes wrongly, which is otherwise silent until
the values turn out to be permuted.

This runs the real backward rather than simulating it, so it reflects the code
that actually executes.

## Memory audit

```python
problems = validate_backward(loss)      # saved but never read
report = memory_report(loss)            # active, saved, live, peak
```

`validate_backward` instruments the engine's own backward and reports tensors a
forward saved that its backward never read. Those are held for the entire
pass, and on a large model that waste is a real fraction of the footprint.

This audit found one immediately: every view node saved its base tensor and
never read it, pinning it for the whole forward-backward pass. Only the spec
and the output shape are needed.

## Exporting

```python
report = inspect(loss, model)
report.to_text()      # human-readable summary
report.to_json()      # machine-readable
report.to_dot()       # Graphviz, edges from producer to consumer
```

The DOT output renders the dataflow directly, which is the fastest way to see a
branch that never reconnects:

```python
pathlib.Path("graph.dot").write_text(report.to_dot())
```

## When a gradient is legitimately zero

Not every zero gradient is a bug. An attention key bias adds `q · b` to every
score in a row, and softmax divides that shift out, so its gradient is exactly
zero rather than approximately zero. There is a test asserting that, so a later
reader does not "fix" it.

The same applies to a saturated activation. A GELU or SiLU has no dead region,
which is why the depth sweep uses one; a ReLU unit can legitimately receive no
gradient once it is fully inactive.

## Checklist

When a deep model trains but underperforms:

1. `check_graph` before backward — anything not connected?
2. `propagation_trace` — does the backward reach the first layer?
3. `gradient_consistency` — are the gradients right, not just present?
4. `gradient_distribution` — is any gradient dead, NaN, or concentrated?
5. `verify_updates` — did every parameter move, and if not why?
6. `validate_shapes` — does any gradient have the wrong shape?