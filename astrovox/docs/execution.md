# Execution and performance

Measure before optimizing. This note covers what the framework measures, what
the measurements said while it was being built, and what is worth changing
next.

## What executes an operation

There is no compiler and no IR. An operation is a `Function` whose forward
calls NumPy directly. That is a deliberate starting point: correctness first,
then measurement, then optimization.

```
model(x)
  └─ Module.__call__           fires forward hooks
       └─ Layer.forward        Linear
            └─ MatMul.apply    Function.apply
                 ├─ np.matmul(a.numpy(), b.numpy())
                 └─ GraphNode attached to the result
backward(loss)
  └─ Engine.backward
       ├─ walk_from            collect nodes
       ├─ sort by sequence_nr   descending: consumers before producers
       └─ per node: combine incoming, call backward, forward to parents
```

Two NumPy calls dominate a forward pass: materializing each view with
`as_strided`, and materializing any strided input that a kernel consumes. A
layer computes `x @ weight.T`, so the transposed weight is materialized every
time. That is a copy PyTorch also avoids, by keeping a differently laid-out
weight, and it is the single clearest target for a fused kernel.

## FLOP accounting

`count_flops` walks the recorded graph and attributes cost per operation. The
convention is that a multiply-add is two flops, so a dense matmul of `(m, k)`
by `(k, n)` costs `2 * m * k * n`, scaled by the batch.

```python
from astrovox.profile import count_flops, count_backward_flops

forward = count_flops(loss)
print(forward.total, forward.top(5))
```

Counted operations include matmul, elementwise arithmetic, reductions,
normalization, softmax, and the losses. Views count as **zero**, because they
move no data; `Materialize` counts, because it does. Embeddings count as zero:
a gather is memory movement, not arithmetic, which is exactly why large
embedding tables are memory bound rather than compute bound.

Counting is static over the recorded graph, so it excludes the backward pass.
`count_backward_flops` doubles a forward cost, which holds for most
differentiable operations, and reports zero for views and embeddings, which have
nothing to differentiate.

Verified against the analytic value: a `(64, 256) @ (256, 512)` plus a
`(64, 512) @ (512, 128)` model is 25,165,824 flops, which is
`2*64*256*512 + 2*64*512*128`.

## Timing

```python
from astrovox.profile import Profiler, benchmark, compare

with Profiler() as prof:
    with prof.region("forward"):
        loss = model(x)
    with prof.region("backward", flops=count_backward_flops(loss).total):
        loss.backward()

print(prof.report())
```

```
region                        calls     total s  per call ms    GFLOP/s
--------------------------------------------------------------------
forward                           1    0.013417       13.417      0.000
backward                          1    0.010803       10.803      4.673
```

`benchmark` warms up before timing. The first call pays for lazily created
buffers and first-touch page faults, which would otherwise dominate a short
run.

## Roofline

Three ratios decide where optimization effort goes:

```python
from astrovox.profile import estimate_bandwidth, estimate_intensity, cache_efficiency

bandwidth = estimate_bandwidth(tensor, seconds)      # bytes per second
intensity = estimate_intensity(flops, bytes_moved)   # flops per byte
residency = cache_efficiency(tensor, working_set)    # 1.0 means it fits
```

Arithmetic intensity above roughly one flop per byte means a kernel is compute
bound and worth improving with better math — a fused kernel, a lower-precision
path. Below that it is bandwidth bound and worth improving with fewer or
narrower accesses. A `Linear` layer is intensity-heavy; an elementwise chain is
not, so the elementwise ops are where a fusion pass would pay.

## Allocation tracking

```python
from astrovox.profile import AllocationTracker

tracker = AllocationTracker()
# wrap the pass you want to measure
print(tracker.report())
```

Counting allocations, bytes, and distinct shapes catches the regression that
matters first in a memory-bound workload: a change that quietly introduces a
temporary per elementwise operation.

## Memory

The figure that matters for training is **saved bytes**: what the forward pass
holds between forward and backward, which is the peak footprint of a step.

```python
from astrovox.profile import memory_report

report = memory_report(loss)
print(report.saved_bytes, report.peak_bytes)
```

Saving is where a backward can waste memory, and `validate_backward` finds it:
a forward that saves a tensor its backward never reads is holding it for the
whole pass. The memory audit found that every view node saved its base tensor
and used only the spec, so every view in a model was pinning memory
needlessly.

In `ReLU`, the input is saved so the mask can be recomputed. That is the right
trade: the mask is one byte per element against the input's four.

## What the measurements said

Building the transformer language model, 87k parameters, 100 steps:

```
validation loss 2.77 -> 2.61 in 14.6s (6.85 steps/s)
```

Profiling that run showed the interesting result: a single `Linear` of width
256 takes about 0.5 ms, and the full two-layer forward takes about 9 ms. The
matmul is not the cost. Graph construction and view materialization dominate.

The cost per forward step breaks down roughly as:

- the two matmuls, which are BLAS and fast,
- a `view` node per transposed weight, each materializing a copy of the weight
  on every call,
- the graph node bookkeeping: one `GraphNode` with context allocation per
  operation.

So the win is not in a faster matmul. It is in avoiding the per-call weight
copy and in making node allocation cheaper. Both are engineering, not
mathematics.

## What is worth doing next

In rough order of value:

1. **Keep weights in both layouts.** A `Linear` could store the transposed
   weight so the hot path never copies. This is what PyTorch does, and it
   removes the largest single cost in a forward pass.
2. **Fuse the elementwise chain.** Normalization, activation, and residual
   addition touch memory repeatedly. One fused pass would move each element
   once instead of three times.
3. **Recompute instead of saving.** For operations where the input is cheap to
   recompute and large to hold — normalization statistics, attention masks —
   storing the input and deriving the rest costs less memory than saving the
   intermediates. This is gradient checkpointing applied per operation rather
   than per segment.
4. **Batch small kernels.** Several hundred tiny matmuls per step would batch
   into one larger call. This needs the compiler layer that does not exist yet.
5. **A real backend.** Everything above assumes NumPy dispatches to BLAS. An
   accelerator backend registered through the `Backend.dispatch` interface
   would bypass that entirely.

## Honest limitations

- CPU only. The `Device` abstraction and backend registry exist and a backend
  implementing `dispatch` would execute kernels, but no CUDA, ROCm, or Metal
  backend is present.
- Attention materializes the full score matrix, so memory grows quadratically
  with sequence length.
- No fusion, no IR, no ahead-of-time compilation, no operator scheduling.
- The FLOP model is analytic and static. It does not model cache behaviour or
  the cost of a materialization beyond counting it as one pass.