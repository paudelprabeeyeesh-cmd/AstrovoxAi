# D-040 Final Report

Session date: 2026-10-15 · Toolchain: Go 1.27.1 on Windows ·
Branch: `fix/checkpoint-persistence-layernorm` (no commits created; all
work is in the working tree).

## 1. State before work

The repository built and its tests passed at HEAD *after* repairing one
pre-existing broken working-tree edit in `internal/tools/tools.go` (a
duplicated method pasted into the middle of another function, which broke
compilation). Two further test failures were pre-existing: a tool-approval
misrouting defect and golden-file tests writing to a non-existent
`testdata/` directory.

## 2. What was done

**Verification of previously untested production code.** `tensor/math`,
`tensor/ops`, `tensor/reduce`, and `tensor/broadcast` had no test files
despite being used by the inference path. All four now have
reference-oracle suites (naive GEMM/conv/pool, analytic gradients, naive
DFT, central finite differences). Writing them found and fixed **nine real
defects**: a fused kernel that discarded its convolution result, a
hardcoded activation slope, two normalization backwards that were wrong
twice over (raw input instead of normalized value, and a missing weight),
two panics (FFT on complex input, quantize on empty), and a broadcasting
routine that reversed output shapes.

**Autograd hardening.** Added gradient rules for Sub, Div, Scale, Relu,
Sigmoid, Tanh, Exp, and Mean (all verified against finite differences),
fixed the sigmoid/tanh adjoint signs, made the tape single-use, made
rule-less nodes a typed error instead of a silent zero, and added
`Detach`.

**New subsystems, behind interfaces, integrated with existing code.**
- `model`: Linear/Sequential/MLP/MSELoss with deterministic init,
  hierarchical parameter naming, and duplicate-parameter detection.
- `internal/checkpoint` file format: versioned, CRC64-checked,
  temp+fsync+rename atomic writes, byte-deterministic, fail-closed reads
  (corruption, truncation, version, and shape lies all refused).
- `inference`: a bounded executor over the existing `runtime.Engine` with
  request limits, deadlines, cancellation, explicit backpressure, graceful
  shutdown, and fixed-cardinality stats.

**Scheduler correctness.** `internal/runtime.Scheduler` panicked on submit
after stop and blocked forever on a full queue. Refusals are now typed,
stop drains accepted work, and every caller and stress test was updated
to assert the new semantics.

**End-to-end acceptance scenario.** `tests/integration/d040_acceptance_test.go`
exercises the real pipeline: model construction, graph -> AstroIR (TIR)
-> optimize -> interpreter execution compared element-for-element against
the autograd engine, analytic gradients, optimizer convergence on a
deterministic regression task (loss 0.925 -> ~1e-18 over 400 steps),
checkpoint save/restore with bit-identical outputs, corruption refusal,
50 concurrent inference requests, cancellation, and resource limits. It
emits a machine-readable JSON summary.

## 3. Command results (actual)

- `go build ./...` — pass
- `go vet ./...` — pass
- `go test ./... -count=1` — **pass: 86 packages, 0 failures**
- `gofmt -l` (module dirs) — clean
- `go test -race` — **not run**: no C toolchain for cgo on this machine
- Benchmarks — pass; numbers in `benchmark-methodology.md`

## 4. Defects fixed (16, each with a regression test)

Build-breaking edit; agent/executor approval split; FusedConvAct result
discarded; hardcoded leaky slope + silent activation pass-through;
LayerNorm/GroupNorm backward adjoints (two bugs each path); FFT panics;
quantize panics; BroadcastShapes reversal; reduce storage-order traversal;
reduce outer-index mapping panic; sigmoid/tanh gradient signs; Mul
swallowed broadcast errors; silent skip for rule-less autograd nodes;
scheduler send-on-closed panic and unbounded blocking; missing testdata
golden-file failures; global-ID test coupling.

## 5. Not done

Race detector, extended fuzzing, profiles, hardware backends, and the
wider D-021..D-039 subsystems (workflows, provider gateway, RAG,
multi-tenancy, distributed coordination). See `limitations.md`.

## 6. Git

No commit was created; changes are in the working tree on
`fix/checkpoint-persistence-layernorm` at `afda7dc8`.
