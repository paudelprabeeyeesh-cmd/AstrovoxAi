# D-040 Compiler and Optimization

## Pipeline

```
graph.Graph --compiler.LowerSingle--> TIR function
  --TIROptimizer--> Module (const fold / DCE / fusion)
  --Interpreter.Execute(params)--> results
```

## Passes (implemented and tested in `compiler/`)

- **Constant folding**: expressions over constant operands are folded;
  the folded form is executed by the interpreter and compared against the
  unoptimized pipeline (equivalence test).
- **Dead-node elimination**: nodes not reachable from the sink are
  removed; verified by post-optimization node counts.
- **Loop/tile fusion and blocking**: the GEMM lowering emits blocked
  loops with a configurable `TileSize`; fusion combines bias and
  activation into the matmul loop nest. Equivalence tests compare
  interpreter output against the same graph executed unoptimized.

## Preconditions / postconditions

- Lowering requires a valid graph (cycles are rejected at construction).
- Optimization preserves semantics by construction: the equivalence tests
  execute both forms on the same inputs and compare within tolerance.
- Where an optimization is not implemented, the code returns
  `CodeUnimplemented` rather than pretending (this rule was applied to
  the fused activation paths fixed in this work).

## What is not here

- No autotuning, no vectorization pass, no machine-specific scheduling.
- `internal/ir`'s passes (LICM, GVN, SCCP, PRE, IPO, Polyhedral) are
  stubs — see ADR-4. If a future session wires them, they must be
  equivalence-tested the same way.
