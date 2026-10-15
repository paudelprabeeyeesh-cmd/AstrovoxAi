# D-041 Forensic Repository Audit

Audit date: 2026-10-15. Scope: full Go module (`github.com/astrovox/astrovox`),
Go 1.27.1, Windows host. This audit was performed by reading the source,
running the build/vet/test suites, and cross-checking documentation claims
against code. Nothing below is aspirational; where a claim could not be
verified it says so.

## 0.1 Baseline (executed)

| Command | Result |
| --- | --- |
| `go build ./...` | pass |
| `go vet ./...` | pass |
| `go test ./... -count=1` | **pass: 86 packages, 0 failures** |
| `gofmt -l` (module dirs) | clean |
| `go test -race` | **blocked**: requires cgo; no C compiler on this host (`gcc` not on PATH) |
| Benchmarks (`go test -bench`, `-benchtime`) | pass; numbers in `benchmark-report.md` |

Pre-existing failures inherited from the D-040 session: none remaining
(the D-040 session fixed the two that existed: a build-breaking edit in
`internal/tools/tools.go` and golden-file tests writing to a missing
`testdata/` directory). Newly introduced failures during this audit: none.

Working tree at audit time: D-040 modifications present (see
`docs/d040/implementation-record.md`), uncommitted, on branch
`fix/checkpoint-persistence-layernorm`. One pre-existing deletion
(`.kilo/plans/master-plan-200-tasks.md`) was preserved untouched.

## 0.2 Package map and dependency direction (actual)

Verified by import inspection. Direction is acyclic.

```
cmd/astrovox, pkg/cli            -> (CLI layer, partially wired)
inference                        -> model, runtime, tensor, internal/errors
model                            -> autograd, tensor, internal/checkpoint, internal/errors
autograd                         -> tensor, tensor/ops, tensor/reduce, internal/errors
compiler                         -> graph, internal/errors
graph                            -> tensor, internal/errors
runtime                          -> internal/runtime, tensor
internal/runtime                 -> internal/errors
internal/checkpoint              -> internal/errors, (os, json, crc64)
tensor                           -> internal/errors, unsafe (typed views)
tensor/ops,reduce,reshape,transpose,broadcast,iterator,memory,math
internal/tools, agent, ai, distributed, backend, kernel, planner, ir, optimizer,
  scheduler, serving, ...        -> mixed; NOT all wired to the core path
python-backend/, sdk/, dashboard/, extension/  -> non-Go (out of scope)
```

The verified core execution path is:

```
inference.Executor -> model.Module -> autograd.Tape -> tensor/ops/math/reduce
graph.Graph -> compiler.LowerSingle -> TIR -> Interpreter
model -> internal/checkpoint (file format)
```

## 0.3 Implementation state of each required subsystem

| Subsystem | Location | Actual state |
| --- | --- | --- |
| Tensor storage/views | `tensor/` | Real: storage+offset+strides, zero-copy views, typed slice views, serialize round-trip, 15 dtypes, float64 arithmetic, checked allocation |
| Tensor ops | `tensor/ops` | Real; softmax/concat/scalar ops added in D-040 with reference tests |
| Kernels | `tensor/math` | Real (GEMM blocked, conv direct/im2col, norms, FFT, quantize, fusion); verified against naive references in D-040 |
| Autograd | `autograd/` | Real; 13 gradient rules, single-use tape, Detach; SGD/Adam |
| Models | `model/` | Real; Linear/Sequential/MLP/MSE + checkpoint bridge (D-040) |
| AstroIR | `graph` + `compiler` | Real: lowering to TIR, const-fold/DCE/fusion optimizer, scalar IR interpreter, equivalence tests |
| SSA IR | `internal/ir` | **Experimental**: analyses real, all optimization passes inert stubs, no production importer |
| Execution planner | `internal/planner` | **Experimental**: memory planner only; MTIR emits unimplemented opcodes |
| Backends | `internal/backend`, `kernels` | CPU real; GPU families are simulation stubs; duplicated dispatch tables in `kernels/` and `internal/kernel/` |
| Runtime scheduler | `runtime`, `internal/runtime` | Real bounded pool; typed refusals; drain-on-stop (D-040 fixes) |
| Inference executor | `inference/` | Real: limits, deadlines, cancellation, backpressure, stats (D-040) |
| Checkpoints | `internal/checkpoint` | Real file format: versioned, CRC64, atomic temp+fsync+rename |
| Serving | `internal/serving` | Different abstraction (float32 batch models); not integrated with `model.Module` |
| Workflows | — | **Absent** |
| Distributed control plane | `internal/distributed` | Simulation only; **not** a control plane |
| Provider gateway | — | **Absent** (Python backend has providers; Go core does not) |
| Retrieval/RAG | `internal/rag` | Stub; **not** wired |
| Multi-tenancy | — | **Absent** in Go core |
| Observability | `internal/logger`, `runtime` counters | Logging exists; no metrics exporter; executor/engine counters fixed-cardinality |
| CLI | `cmd/astrovox`, `pkg/cli` | Flag dispatch exists; subcommands are thin; no machine-readable output |
| CI | `.github/workflows/` | build/test/vet/security/benchmark gates exist; not executed locally |

## 0.4 Defects found during the D-040 session (context, all fixed)

16 defects, each with a regression test — see
`docs/d040/repository-audit.md` §Defects. Most load-bearing for D-041:
tensor/math backward math (x2), broadcasting shape reversal, reduction
traversal on views, reduction index-mapping panic, autograd silent zeros
and adjoint signs, scheduler panic-on-stop.

## 0.5 Duplicate abstractions and boundary issues

1. **Two dispatch systems**: `kernels/dispatch.go` + `kernels/registry.go`
   and `internal/kernel/{registry,dispatch,selector,autotune,cache}.go`.
   Not unified; the core path uses direct calls.
2. **Two "IR"s**: `graph`+`compiler` (real) vs `internal/ir` (stub passes).
3. **Two schedulers**: `internal/scheduler` (DAG heuristics) vs
   `internal/runtime` (the pool actually used by `runtime.Engine`).
4. **Two model abstractions**: `internal/serving.Model` (float32 batch)
   vs `model.Module` (tensor+autograd). D-041 builds on `model.Module`
   and documents this in ADR-2 rather than unifying (unification would
   churn a package nothing on the core path imports).
5. **Global state**: `internal/ir` uses a global node-ID counter (already
   caused a test-order defect, fixed in D-040); `autograd` has none;
   `tensor` has none.

## 0.6 Risks carried into this mission

| Risk | Severity | Mitigation in this mission |
| --- | --- | --- |
| No race detector locally | High | Document; CI runner executes it; deterministic synchronization in all new concurrency tests |
| Untested production kernels (now fixed for tensor/math; other packages unaudited) | Medium | New work adds tests at the boundary it touches |
| Simulation backends mistaken for capability | Medium | Capability records name CPU as the only verified backend |
| `internal/ir` stubs could be wired by mistake | Low | ADR: compiler TIR is the IR of record |
| Duplicate schedulers invited drift | Medium | ADR: one scheduler; registry built on `inference.Executor` |

## 0.7 Gate 0 statement

Baseline is reproducible (commands and results above), repository state is
documented, critical risks are listed with owners and mitigations, and the
dependency plan for this mission is in `implementation-plan.md`.
Implementation may proceed.
