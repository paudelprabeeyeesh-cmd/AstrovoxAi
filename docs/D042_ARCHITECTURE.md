# ASTROVOX AI — MISSION D-042 ARCHITECTURE

**Date:** 2026-10-16  
**Repository:** `github.com/astrovox/astrovox` (Go module, go 1.27, zero external dependencies)  
**Branch:** `main` @ `74db1493`

---

## 1. Execution contract (Phase 1)

All core packages agree on the following semantics, verified by contract tests:

| Concern | Contract | Enforced by |
| --- | --- | --- |
| Tensor shape/stride/dtype | Strided views with offset; dtype is `float64` for arithmetic; int/bool refused with typed error | `tensor/`, `tensor/ops` |
| Device | CPU only; GPU backends are simulation stubs, never silently selected | `internal/backend/` |
| Ownership | Tensors returned by ops are freshly allocated or documented views; caller owns returned buffers | `tensor/`, `model/` |
| Mutation | Parameters mutated only through optimizer `Step`; tensors otherwise immutable after creation | `autograd/`, `model/` |
| Error handling | Typed errors via `internal/errors` codes: `CodeInvalidArgument`, `CodeTimeout`, `CodeCancelled`, `CodeResourceExhausted`, `CodeCorruptData`, `CodeUnimplemented`, `CodeInternal`; no string matching | All packages |
| Numerical failure | NaN/Inf in gradients → gradients zeroed (documented policy), trainer skips step | `autograd/clip.go`, `model/trainer.go` |
| Cancellation | `context.Context` flows from inference request → model forward; deadline enforced at admission and during execution | `inference/` |
| Deadlines | Already-expired deadline refused at submission; deadline during execution → `CodeTimeout` | `inference/` |
| Model parameter naming | Hierarchical names (`mlp.fc0.W`); `Flatten` refuses duplicate parameters | `model/` |
| Serialization | Checkpoint: versioned, CRC64, atomic temp+fsync+rename; restore requires exact name/shape match | `internal/checkpoint/`, `model/persist.go` |
| Resource limits | `inference.Limits` (inputs/elements/outputs per request); executor worker/queue bounds | `inference/` |
| Queue capacity | Refusal with `CodeQueueFull`; never silent blocking | `internal/scheduler/`, `runtime/` |
| Shutdown | `Stop` drains accepted work; submissions after stop → `CodeCancelled` | `internal/scheduler/`, `runtime/` |
| Thread safety | No package-level mutable state in core tensor/autograd/model paths; mutexes only at admission/queue boundaries | All core packages |

### Contract tests (Phase 1)

Contract tests live in `tests/integration/d042_contract_test.go` and verify:

- A checkpoint written by `WriteFile` is readable by `ReadFile` and `Inspect` (round-trip).
- A checkpoint with a single flipped byte fails `ReadFile` with `CodeCorruptData`.
- A checkpoint with a future version fails with `CodeVersionMismatch`.
- An inference request with an expired deadline fails at submission with `CodeTimeout`.
- An inference request exceeding element limits fails with `CodeResourceExhausted`.
- A submission after `Executor.Shutdown` fails with `CodeCancelled`.
- Two `model.Module` instances with the same seed produce bit-identical parameters.
- `GradNorm`/`ClipGradients` on a zero-gradient variable returns 0 without error.
- `ClipGradients` with `maxNorm <= 0` or `NaN` fails with `CodeInvalidArgument`.

---

## 2. Layered architecture

```
CLI (cmd/astrovox d041 subcommands)         Phase 19 (D-041)
  -> version, doctor, checkpoint inspect/verify,
     model inspect/validate/run, graph validate,
     runtime status, config validate (JSON output)

Inference serving surface                  Phase 8 (D-042)
  inference.Executor  (bounded admission, deadlines,
                       cancellation, stats)
  inference.Registry  (model registration, versions,
                       health, load/unload)

Training                                    Phases 3, 4 (D-041/D-042)
  model.Trainer  (reproducible runs, checkpoint/resume)
  model schedules  (constant/step/cosine LR)
  autograd.ClipGradients / autograd.GradNorm

Compute core (verified, D-041)              Phases 1-2
  tensor + tensor/{ops,math,reduce,broadcast}
  autograd (13 rules, single-use tape)
  model.Module / MLP
  graph -> compiler.TIR -> Interpreter      (AstroIR path of record)

Persistence                                 Phase 5 (D-041)
  internal/checkpoint (versioned + CRC64 +
   atomic file format); optimizer state +
   RNG/config provenance via Trainer

Verification                                Phases 14, 15
  fuzz targets at parser/persistence boundaries
  tests/integration acceptance scenario
```

## 3. Dependency direction (verified acyclic)

```
runtime          -> internal/runtime, tensor
inference        -> model, runtime, tensor, internal/errors
model            -> autograd, tensor, internal/checkpoint, internal/errors
autograd         -> tensor, tensor/ops, tensor/reduce, internal/errors
compiler         -> graph, internal/errors
graph            -> tensor, internal/errors
internal/compiler -> graph, tensor
internal/ir      -> tensor
internal/kernel  -> tensor
internal/optimizer -> graph
internal/planner -> (standalone)
internal/scheduler -> (standalone)
internal/serving -> tensor
internal/tools   -> tensor, internal/errors
kernels          -> tensor
```

**No import cycles.** `internal/*` stays internal.

## 4. What is NOT in the Go core (documented limitations)

| Subsystem | Status | Reason |
| --- | --- | --- |
| Workflow engine | Absent | No workflow package in Go core; deferred (Phase 9) |
| Distributed control plane | Simulation only | `internal/distributed` is not a real control plane; deferred (Phase 10) |
| Provider gateway | Absent | Python backend has providers; Go core does not; deferred (Phase 11) |
| Retrieval/RAG | Stub | `internal/rag` exists but not wired; deferred (Phase 12) |
| Multi-tenancy | Absent | No tenant identity in Go core; deferred (Phase 14) |
| GPU acceleration | Untested | Simulation stubs only; no hardware; CPU is verified backend |
| Race detector | Blocked | No C toolchain for cgo on this host |
| Metrics exporter / histograms | Absent | Fixed-cardinality counters only; no exporter |

## 5. Key decisions (ADRs)

- **ADR-1:** Build on the existing core; no parallel engine.
- **ADR-2:** `model.Module` is the model abstraction of record; `internal/serving.Model` is a separate float32-batch abstraction, left as-is.
- **ADR-3:** One scheduler. The registry composes `inference.Executor`; no new pool.
- **ADR-4:** AstroIR = compiler TIR; `internal/ir` remains Experimental (inert optimization passes).
- **ADR-5:** Phases 9-10 (workflows, distributed) deferred; specified in plan with explicit reasons.
