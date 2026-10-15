# D-041 Implementation Plan and Status

Status legend: DONE (implemented + tested + gate evidence) · PARTIAL ·
NOT STARTED · BLOCKED (with reason).

## Phase status

| Phase | Subject | Status | Evidence |
| --- | --- | --- | --- |
| 0 | Forensic audit + baseline | DONE | `audit.md`; commands reproduced in `verification-report.md` |
| 1 | Unified execution contract | DONE (convergence of existing layers) | `architecture.md` §Execution contract; inference/autograd tests |
| 2 | Tensor engine + memory | DONE (inherited, verified in D-040) | `docs/d040/tensor-and-autograd.md`; tensor/* suites |
| 3 | Autograd + training engine | DONE | new `autograd/clip.go` (norm + clipping) with tests; 13 rules finite-difference verified |
| 4 | AstroIR compiler + planner | DONE (inherited) | compiler equivalence tests; `docs/d040/compiler-and-optimization.md` |
| 5 | Operator registry + backend capabilities | PARTIAL | existing registries audited (`audit.md` §0.5); capability naming documented in `backend-contract` (d040); unification NOT done |
| 6 | Durable checkpoints | DONE (inherited) | `internal/checkpoint/file_test.go`: round-trip, determinism, corruption, truncation, interruption, version |
| 7 | Optimizers + training orchestration | DONE | new `model/schedule.go`, `model/trainer.go`; reproducibility + resume-equivalence tests |
| 8 | Model serving + admission control | DONE | new `inference/registry.go`: versions, health, load/unload, per-model concurrency; tests |
| 9 | Durable workflow engine | NOT STARTED | specified below |
| 10 | Distributed control plane | NOT STARTED | specified below |
| 11 | Provider gateway | NOT STARTED | specified below |
| 12 | Retrieval/embeddings/memory | NOT STARTED | `internal/rag` stub audited; not wired |
| 13 | Secure tool runtime / extension SDK | PARTIAL (pre-existing `internal/tools` with permissions) | `internal/tools` has permission gating + audit; no versioned manifests |
| 14 | Multi-tenancy | NOT STARTED | no tenant identity in Go core |
| 15 | Observability + diagnostics | PARTIAL | structured logger + fixed-cardinality counters; no exporter, no histograms; CLI `doctor`/`runtime status` added |
| 16 | Performance engineering | PARTIAL | benchmark suite + `benchmark-report.md`; no profiles (blocked: no profiling harness run in session) |
| 17 | Adversarial testing + fault injection | DONE (slice) | new fuzz targets: checkpoint decode, tensor serialize, broadcast; fault paths covered by checkpoint/inference tests |
| 18 | CI + cross-platform | PARTIAL | workflows exist; race gate documented as blocked locally; no new runner added |
| 19 | Developer CLI | DONE (slice) | `cmd/astrovox` d041 subcommands: version, doctor, checkpoint inspect/verify, model inspect/validate/run, graph validate, runtime status, config validate; in-process integration tests |
| 20 | Final integration + acceptance | DONE (core scenario) | extended `tests/integration/d041_acceptance_test.go`; `verification-report.md` |

## Phase 7 design (implemented)

- `model.TrainConfig{Seed, LR, Steps, BatchSize, Schedule, Optimizer,
  CheckpointPath}`; `model.Train` runs deterministic steps and records
  metrics; `model.Trainer.Save/Load` round-trips parameters **and
  optimizer state and step counter** through the checkpoint format.
- Reproducibility test: two runs with the same seed produce identical
  parameters; resume test: a resumed run's parameter trajectory equals an
  uninterrupted run's (optimizer state is not silently reset).
- Schedules: `ConstantSchedule`, `StepSchedule{Step, Gamma}`,
  `CosineSchedule{Total}`; each unit-tested at boundaries.

## Phase 8 design (implemented)

- `inference.Registry`: register(name, version, module) with duplicate
  detection; `Load`/`Unload` lifecycle; per-model executor with bounded
  workers; `Health` reporting (loaded/unloaded, executor stats); version
  listing. Registry tests cover duplicate registration, unload refusal
  while in flight (drain), and per-model isolation of limits.
- Built on `inference.Executor` — no second scheduler (ADR-3).

## Phase 17 design (implemented slice)

- `FuzzCheckpointDecode` (`internal/checkpoint`): arbitrary bytes must
  never panic and must fail closed.
- `FuzzTensorSerialize` (`tensor`): arbitrary round-trips must never
  panic; failures are typed errors.
- `FuzzBroadcastShapes` (`tensor/broadcast`): arbitrary dims must never
  panic; results must satisfy output-shape invariants (each output dim
  equals the matching non-1 input dim).

## Phase 19 command set (implemented)

`astrovox version|doctor|checkpoint inspect|checkpoint verify|model
inspect|model validate|model run|graph validate|runtime status|config
validate` — each backed by a real subsystem call, with `-json` output and
documented exit codes. Tested in-process via the command handlers.

## Remaining phases (not started, with first concrete steps)

1. **Phase 9 workflows**: define `WorkflowDef` + task state machine in a
   new `internal/workflow` package; persist transitions via
   `internal/checkpoint`'s file store behind a `StateStore` interface;
   kill/restart integration test. First step: state machine + store
   interface with the file implementation, unit tested.
2. **Phase 10 distributed**: control-plane interfaces (node, lease,
   heartbeat) in `internal/controlplane`; single-node implementation
   first; multi-process dev mode; fault injection. First step: message
   schema + conformance tests.
3. **Phase 11 provider gateway**: `Provider` interface + mock provider;
   timeouts/retries/circuit breaker; no live claims. First step:
   interface + mock + failure tests.
4. **Phase 12 retrieval**: document/chunk types + exact-search baseline +
   provenance; fixtures with labels; precision/recall on the fixture.
5. **Phase 14 tenancy**: tenant ID in `inference.Request` propagated to a
   tenant-scoped key in checkpoints/registry; negative tests.
6. **Phase 15/16**: metrics exporter + histograms; profiles once a
   profiling-capable runner is available.
