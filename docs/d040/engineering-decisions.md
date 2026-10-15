# D-040 Engineering Decisions

## ADR-1: Linear layers store W as [in, out]

**Context.** The conventional PyTorch layout is [out, in], requiring a
transposed view in forward.

**Decision.** `model.Linear` stores `[in, out]`.

**Rationale.** Forward becomes `x @ W + b` with zero transposed views.
The autograd adjoints for MatMul then write directly to the stored
parameter, which removes a whole class of view/lifetime bugs the audit
found elsewhere in the codebase. Checkpoints record the shape, so the
layout is self-describing.

## ADR-2: One approval decision, enforced at the executor

**Context.** The agent and the tool executor each had an approver with
different defaults, so an approved call could be refused (and mislabeled
as a budget hit) — or vice versa.

**Decision.** Approval is decided once (agent layer) and installed on the
executor; the executor's gate re-checks that decision rather than holding
a second default.

**Rationale.** Two gates with different defaults cannot be reasoned about
and already produced a silent functional bug. Defense in depth is
preserved: the executor still refuses when there is no decision.

## ADR-3: The tape is single-use; rule-less nodes are errors

**Context.** The old tape could be replayed (double-accumulating
gradients), silently skipped nodes with no gradient rule (silent zero
gradient), and continued differentiating against values an optimizer had
replaced.

**Decision.** `Backward` errors on replay and on rule-less nodes. An
unreachable node contributes zero (standard stop-gradient semantics, which
keeps `Detach` usable).

**Rationale.** The mission explicitly forbids silently returning zero
gradients for unsupported operations. Unreachable-but-legal nodes must
still work, hence zero there and an error for the unsupported case.

## ADR-4: The compiler TIR is the AstroIR of record; internal/ir is not extended

**Context.** Two IR-like systems exist. `graph -> compiler TIR ->
interpreter` is a real, tested pipeline. `internal/ir` (SSA) has real
analyses but every optimization pass is an inert stub and nothing imports
it.

**Decision.** Build on the compiler TIR path; do not extend `internal/ir`.

**Rationale.** Adding features to a graph that cannot execute would
produce another unverified subsystem. `internal/ir` is labeled
Experimental in component status instead.

## ADR-5: One scheduler

**Context.** The repo contains several pool-like schedulers.

**Decision.** The inference executor uses the existing
`runtime.Engine` (over `internal/runtime.Scheduler`).

**Rationale.** A second competing scheduler would duplicate queue
semantics and invariants. The pool was hardened first (typed refusals,
drain-on-stop), which fixed a real panic-on-stop defect.

## ADR-6: Checkpoint writes are temp+fsync+rename, never in-place

**Context.** In-place writes can truncate the last good checkpoint on a
crash mid-write.

**Decision.** Write to a temp file in the destination directory, fsync it,
best-effort fsync the directory, then rename. Version and CRC64 are
validated on every read; older/newer versions are refused with
`CodeVersionMismatch`.

**Rationale.** Durability and fail-closed validation are the point of the
feature. Directory fsync is best-effort because it is not uniformly
supported; that limitation is documented rather than hidden.

## ADR-7: Refuse unsupported work loudly

**Context.** Several kernels and fused paths passed unsupported cases
through unchanged (fused activations, quantize-on-empty, FFT on complex
input), producing wrong results or panics.

**Decision.** Unsupported inputs return typed errors (`CodeUnimplemented`,
`CodeCorruptData`, ...). Where a fallback is correct (e.g. materializing a
non-contiguous view), it is taken and documented.
