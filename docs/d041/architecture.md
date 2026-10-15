# D-041 Architecture

## Scope decision

D-041 is a 20-phase program. This document describes the architecture as
it stands after the phases implemented in this session, with each phase's
status marked. The full phase list and what remains is in
`implementation-plan.md` and `limitations.md`.

## Layered view (as implemented)

```
CLI (cmd/astrovox: d041 subcommands)            Phase 19
  -> docs/inspect/validate/status, JSON output

serving surface (inference package)              Phase 8
  inference.Executor  (bounded admission, deadlines, cancellation, stats)
  inference.Registry  (model registration, versions, health, lifecycle)

training (model package)                         Phases 3, 7
  model.Trainer       (reproducible runs, checkpoint/resume)
  model schedules     (constant/step/cosine LR)
  autograd.ClipGradients / autograd.GradNorm

compute core (unchanged, verified)               Phases 1-4
  tensor + tensor/{ops,math,reduce,broadcast}
  autograd (13 rules, single-use tape)
  model.Module / MLP
  graph -> compiler.TIR -> Interpreter (AstroIR path of record)

persistence (internal/checkpoint)                Phase 6
  versioned + CRC64 + atomic file format;
  optimizer state + RNG/config provenance via Trainer

verification                                       Phases 17, 20
  fuzz targets at parser/persistence boundaries
  tests/integration acceptance scenario (extended)
```

## Key decisions (ADRs in `docs/d041/adr/`)

- ADR-1: Build on the existing core; no parallel engine.
- ADR-2: `model.Module` is the model abstraction of record;
  `internal/serving.Model` is left alone (documented divergence).
- ADR-3: One scheduler. The registry composes `inference.Executor`;
  no new pool.
- ADR-4: AstroIR = compiler TIR; `internal/ir` remains Experimental.
- ADR-5: Phases 9-14 (workflows, distributed, providers, retrieval,
  tenancy) are **not** implemented in this session; they are specified in
  `implementation-plan.md` with their gates and are not claimed.

## Execution contract convergence (Phase 1 status)

The layers now agree on the following, verified by tests:

- **Cancellation**: context flows from executor -> model -> (tape-less)
  forward; the executor checks the context before and after execution;
  deadlines are enforced at admission and during execution.
- **Error classification**: `internal/errors` codes are used uniformly:
  `CodeInvalidArgument` (input), `CodeTimeout`, `CodeCancelled`,
  `CodeResourceExhausted` (limits), `CodeCorruptData` (persistence),
  `CodeUnimplemented` (unsupported), `CodeInternal`. New code adds no new
  codes and no sentinel-string matching.
- **Resource budgets**: `inference.Limits` (inputs/elements/outputs) and
  executor worker/queue bounds; `autograd.GradNorm`/`ClipGradients` bound
  gradient magnitude; trainer config bounds steps/batch.
- **Structured results**: `inference.Result` carries outputs, error,
  wait/exec durations; `Executor.Stats()` is fixed-cardinality.

## Data ownership rules

- Parameters are owned by the module that created them; the trainer only
  replaces `Var.Value` through optimizer steps; `RestoreFromCheckpoint`
  copies into the existing parameter storage (never aliases file buffers).
- Tensors returned from ops are freshly allocated or documented views;
  checkpoint payload buffers are copied into tensors at load.
- The registry owns model instances and unloads them on `Unload`;
  in-flight requests holding an executor reference complete before the
  executor shuts down (drain semantics from the scheduler).
