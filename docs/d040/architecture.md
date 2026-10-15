# D-040 Architecture

## What exists today (verified)

```
model.Module (parameters + forward)
  |-- autograd.Tape (reverse-mode differentiation)
  |-- tensor core (values, views, ops, math kernels)
  └-- inference.Executor (bounded scheduler: workers, queue, deadlines)

ASTROIR PATH (graph representation and execution)
graph.Graph --compiler.LowerSingle--> compiler TIR (versioned IR)
  --TIROptimizer (const fold / DCE / fusion)--> Module
  --Interpreter.Execute--> float64 results   (CPU reference backend)

TRAINING PATH
model.MLP -> MSELoss -> Tape.Backward -> autograd SGD/Adam
  -> checkpoint.FileCheckpoint (atomic, checksummed, versioned file)
  -> RestoreFromCheckpoint (exact-name/shape validation)
```

## Boundaries added in this work

### `model` package (new)

- `Module` interface: `Forward(tape, x)`, `Parameters()`,
  `NamedParameters()`, `Name()`.
- `Linear` stores W as `[in, out]` so forward is a plain `x @ W + b`
  (no transposed views, adjoints flow straight to parameters).
- `Sequential`/`MLP` compose modules; `MLP` is the deterministic
  demonstration model (3->4->1 and larger).
- `MSELoss` built from differentiable ops (Sub, Mul, Mean).
- `ToCheckpoint`/`RestoreFromCheckpoint` bridge to the file format;
  restore requires an exact name/shape match — no partial restores.
- `Flatten` produces hierarchical names (`mlp.fc0.W`) and refuses a
  parameter reachable twice.

### `inference` package (new)

- Single admission point: validate -> deadline -> bounded queue -> bounded
  workers -> graceful shutdown.
- Every refusal is a typed error: `CodeInvalidArgument`,
  `CodeResourceExhausted`, `CodeTimeout`, `CodeCancelled`,
  `CodeQueueFull`.
- Builds on the existing `runtime.Engine` rather than a second scheduler.
- `ModuleExecutable` adapts any `model.Module` without a tape.

### `internal/checkpoint` file format (new)

- Layout: magic `AXCK` + version + JSON header + little-endian f64
  payload + CRC64 (ECMA) trailer.
- Atomic write: temp file in the destination directory, `fsync`, best
  effort directory sync, `rename`.
- Deterministic: identical state produces byte-identical files.
- Reads validate framing, version, checksum, header, and shape/length
  agreement. Corrupt or truncated files fail closed.

### Dependency direction

```
inference -> model -> autograd -> tensor
inference -> runtime -> internal/runtime
model -> internal/checkpoint -> (os, crc64, json)
compiler -> graph -> tensor
```

No cycles; no package imports a concrete provider where an interface
suffices; `internal/*` stays internal.

## Where things live

- Tensor core: `tensor/` (dtype, shape, storage, views, serialize).
- Ops/kernels: `tensor/ops`, `tensor/math`, `tensor/reduce`,
  `tensor/transform` (subscription/squeeze/scatter/where).
- Graph/IR/execution: `graph`, `compiler` (TIR + interpreter).
- Models/training: `model`, `autograd`.
- Scheduling: `runtime` (public), `internal/runtime` (pool).
- Persistence: `internal/checkpoint`.

## Deliberate non-additions

- No second scheduler: `runtime.Engine` is the only worker pool used by
  the runtime and the new inference executor.
- No new GPU backend: unverified hardware claims are worse than none.
- `internal/ir` and `internal/optimizer` are left as-is (unused by
  production) rather than extended, because the compiler TIR is the real
  IR path; see engineering-decisions.md ADR-4.
