# ASTROVOX AI — MISSION D-042 IMPLEMENTATION PLAN

**Date:** 2026-10-16  
**Branch:** `main` @ `74db1493`  
**Baseline:** `go build ./...`, `go vet ./...`, `go test ./...` — 86 packages, 0 failures

---

## Phase status legend

DONE = implemented + tested + gate evidence  
PARTIAL = implemented, partially verified  
NOT STARTED = specified, not implemented  
BLOCKED = cannot proceed in this environment (reason documented)

---

## Phase status table

| Phase | Subject | Status | Evidence |
| --- | --- | --- | --- |
| 0 | Forensic audit + baseline | DONE | `docs/D042_AUDIT.md`; baseline: 86 pkgs, 0 failures |
| 1 | Execution contract | DONE (convergence of existing layers) | `docs/D042_ARCHITECTURE.md` §1; inference/autograd tests |
| 2 | Tensor engine + memory | DONE (inherited, verified D-041) | `docs/d040/tensor-and-autograd.md`; tensor/* suites |
| 3 | Autograd + gradient verification | DONE | `autograd/clip.go` (norm + clipping) + tests; 13 rules finite-difference verified |
| 4 | Optimizers + training orchestration | DONE | `model/schedule.go`, `model/trainer.go`; reproducibility + resume-equivalence tests |
| 5 | Durable checkpoints | DONE (inherited) | `internal/checkpoint/file_test.go`: round-trip, determinism, corruption, truncation, interruption, version |
| 6 | AstroIR compiler + planner | DONE (inherited) | Compiler equivalence tests; `docs/d040/compiler-and-optimization.md` |
| 7 | Operator registry + backend capabilities | PARTIAL | Registries audited (`audit.md` §0.5); capability naming documented; unification NOT done |
| 8 | Model serving + admission control | DONE | `inference/registry.go`: versions, health, load/unload, per-model concurrency; tests |
| 9 | Durable workflow engine | NOT STARTED | Specified below |
| 10 | Distributed control plane | NOT STARTED | Specified below |
| 11 | Provider gateway | NOT STARTED | Specified below |
| 12 | Retrieval/embeddings/memory | NOT STARTED | `internal/rag` stub audited; not wired |
| 13 | Secure tool runtime / extension SDK | PARTIAL (pre-existing `internal/tools` with permissions) | `internal/tools` has permission gating + audit; no versioned manifests |
| 14 | Multi-tenancy | NOT STARTED | No tenant identity in Go core |
| 15 | Observability + diagnostics | PARTIAL | Structured logger + fixed-cardinality counters; no exporter, no histograms; CLI `doctor`/`runtime status` added (D-041) |
| 16 | Performance engineering | PARTIAL | Benchmark suite + `docs/d040/benchmark-methodology.md`; no profiles (blocked: no profiling harness run) |
| 17 | Adversarial testing + fault injection | DONE (slice) | New fuzz targets: checkpoint decode, tensor serialize, broadcast; fault paths covered by checkpoint/inference tests |
| 18 | CI + cross-platform | PARTIAL | Workflows exist; race gate documented as blocked locally; no new runner added |
| 19 | Developer CLI | DONE (slice) | `cmd/astrovox` d041 subcommands; in-process integration tests |
| 20 | Final integration + acceptance | DONE (core scenario) | Extended `tests/integration/d040_acceptance_test.go`; `docs/d040/final-report.md` |

---

## Phase 7 design (implemented, D-041)

- `model.TrainConfig{Seed, LR, Steps, BatchSize, Schedule, Optimizer, Loss, ClipGradNorm, CheckpointPath, ModelName}`.
- `model.Train` runs deterministic steps and records metrics.
- `model.Trainer.Save/Load` round-trips parameters **and** optimizer state and step counter through the checkpoint format.
- Reproducibility test: two runs with same seed produce identical parameters.
- Resume test: resumed run's parameter trajectory equals uninterrupted run's (optimizer state is not silently reset).
- Schedules: `ConstantSchedule`, `StepSchedule{Step, Gamma}`, `CosineSchedule{Total}`; unit-tested at boundaries.

## Phase 8 design (implemented, D-041)

- `inference.Registry`: register(name, version, module) with duplicate detection; `Load`/`Unload` lifecycle; `Health` reporting; version listing.
- Registry composes `Executor` — no second scheduler (ADR-3).
- Registry tests: duplicate registration, unload refusal while in flight (drain), per-model isolation of limits.

## Phase 17 design (implemented slice, D-042)

- `FuzzCheckpointDecode` (`internal/checkpoint`): arbitrary bytes must never panic and must fail closed.
- `FuzzTensorSerialize` (`tensor`): arbitrary round-trips must never panic; failures are typed errors.
- `FuzzBroadcastShapes` (`tensor/broadcast`): arbitrary dims must never panic; output-shape invariants hold.

## Remaining phases (first concrete steps)

### Phase 9 — Durable workflow engine

1. Define `WorkflowDef` + task state machine (`Pending → Ready → Running → Succeeded`, with failure/retry/cancellation/recovery transitions) in a new `internal/workflow` package.
2. Persist transitions via `internal/checkpoint`'s file store behind a `StateStore` interface.
3. Kill/restart integration test: kill process mid-workflow, restart, verify recovery without corruption.
4. Idempotency keys for externally visible effects; at-least-once semantics documented explicitly (no exactly-once claims).

### Phase 10 — Distributed control plane

1. Control-plane interfaces (node identity, lease, heartbeat) in `internal/controlplane`.
2. Single-node implementation using the same interfaces.
3. Message schema + conformance tests.
4. Multi-process dev mode; worker registration/deregistration; lease renewal/expiry; duplicate-result handling.
5. Fault injection: dropped connections, delayed messages, duplicate delivery, worker termination.
6. No consensus claims; single coordinator remains a documented failure domain.

### Phase 11 — Provider gateway

1. `Provider` interface + mock provider.
2. Timeouts/retries/circuit breaker; structured errors.
3. No live provider claims without a real successful integration test.
4. Credentials never in source/logs/fixtures; environment variables only.

### Phase 12 — Retrieval/embeddings/memory

1. Document/chunk types + exact-search baseline + provenance.
2. Embedding dimension validation; metadata filtering.
3. Fixtures with labels; precision/recall on fixture.
4. Retrieved content treated as untrusted; separate from system policy.

### Phase 14 — Multi-tenancy

1. Tenant ID propagated through `inference.Request`.
2. Tenant-scoped keys in checkpoints/registry.
3. Negative tests: cross-tenant access rejected at service and storage boundaries.

### Phase 15 — Observability

1. Metrics exporter + histograms (bounded cardinality).
2. Profiles once a profiling-capable runner is available.
3. CLI `doctor`/`runtime status` (already present from D-041).

## Deferred work (explicit, with reasons)

| Phase | Reason |
| --- | --- |
| 9 (workflow engine) | Requires durable state machine + storage abstraction beyond current Go core surface; out of scope for one session |
| 10 (distributed control plane) | Requires multi-process coordination and network; no second machine/credential available in this environment |
| 11 (provider gateway) | Requires live provider credentials; out of scope |
| 12 (retrieval/RAG) | `internal/rag` is a stub; requires embedding provider integration; out of scope |
| 14 (multi-tenancy) | Requires tenant identity model across the Go core; out of scope |

## Scope priorities (per mission rules)

Correctness, persistence, local execution, and the end-to-end acceptance test take priority over speculative distributed or GPU features. No hardware-dependent claims are made without hardware verification.
