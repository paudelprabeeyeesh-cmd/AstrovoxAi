# D-040 Implementation Record

All entries below were executed in this session on
`branch fix/checkpoint-persistence-layernorm`. No commits were created.

## Files added

### Source
- `model/model.go` — Module interface, Parameter, Flatten (hierarchical names, duplicate detection)
- `model/linear.go` — Linear layer ([in,out] layout), Activation type
- `model/sequential.go` — Sequential container, MLP
- `model/loss.go` — MSELoss
- `model/persist.go` — ToCheckpoint / RestoreFromCheckpoint
- `inference/inference.go` — Request/Result/Future/Stats/Executor (limits, deadlines, backpressure, shutdown)
- `inference/module.go` — ModuleExecutable adapter
- `internal/checkpoint/file.go` — versioned, checksummed, atomic file format

### Tests
- `tensor/math/math_test.go` — GEMM transposes/block-crossing, conv direct/im2col vs naive, maxpool, layernorm/groupnorm forward + finite-difference backward, RMSNorm, FFT vs DFT, all fused activations incl. leaky slope, BLAS primitives, int8 round-trip
- `tensor/ops/ops_test.go` — elementwise + broadcast, unary + new scalar ops, softmax (stability + dims), concat, matmul/dot, dtype rejection
- `tensor/reduce/reduce_test.go` — sum/mean/var/std/min/max/prod/argmax/cumsum/norm, non-contiguous regression (transpose/slice), dtype rejection
- `tensor/broadcast/broadcast_test.go` — rank-mismatch shapes, rejection, expand strides
- `autograd/autograd_grad_test.go` — sub/div/scale gradients, activation gradients vs finite differences, mean, broadcast, diamond accumulation, single-use tape, rule-less node error, detach, MLP finite differences, fresh-tape training loop
- `model/model_test.go` — forward vs reference, deterministic init, gradient flow, MLP/sequential naming, shared-parameter rejection
- `internal/checkpoint/file_test.go` — round-trip, byte determinism, corruption sweep, truncation, interrupted-write, future version, header/shape lies, validation rejections, inspect
- `inference/inference_test.go` — single request, validation refusals, concurrency, deadline during execution, cancellation, backpressure, model failure, shutdown, end-to-end through a real model
- `tests/integration/d040_acceptance_test.go` — the 9-stage end-to-end scenario + JSON summary artifact
- `model/bench_test.go`, `inference/bench_test.go` — forward, loss, checkpoint save/load/restore, executor throughput and queue latency

## Files modified (fixes with regression coverage)

- `internal/tools/tools.go` — repaired the mangled working-tree edit; `Result.Reason` classifies skips ("budget"/"approval"); `BudgetConfig` accessor defined once
- `internal/tools/agent/agent.go` — adapter installs the agent's approver on the executor; skips classified correctly
- `internal/tools/agent/debug_test.go` — was leftover debug scratch; converted into a real regression test
- `tensor/math/fused_act.go` — FusedConvAct writes the conv result; leaky slope parameterized; unsupported activations error
- `tensor/math/norm.go` — LayerNorm/GroupNorm backward: xHat + weight in the adjoint
- `tensor/math/fft.go` — typed errors instead of panics on non-float64 input
- `tensor/math/quant.go` — empty-tensor guards
- `tensor/broadcast/broadcast.go` — output indexing fixed for rank-mismatched broadcasts
- `tensor/reduce/reduce.go` — contiguity materialization; outer->output index mapping; CumSum/AddSafe/argReduce guards
- `tensor/reduce/plan.go` — Plan carries OuterOutputDims (input->output dim mapping)
- `autograd/autograd.go` — single-use tape; zero for unreachable; error for rule-less; Detach
- `autograd/ops.go` — Sub/Div/Scale/Relu/Sigmoid/Tanh/Exp/Mean; expandReducedGrad; Mul error propagation; sigmoid/tanh adjoint signs
- `internal/runtime/runtime.go` — typed Submit refusals, drain-on-stop, no send-on-closed panic, QueueLen
- `runtime/execution.go`, `runtime/stream.go` — propagate typed errors; QueueLen
- `runtime/runtime_test.go`, `runtime/stress_test.go`, `runtime/bench_test.go`, `internal/runtime/*_test.go` — updated for the new signatures; stress tests now assert backpressure instead of assuming unbounded queueing
- `tests/stability/stability_test.go` — backpressure-aware submission
- `tests/integration/integration_test.go` — use returned IR node IDs (`-count=2` fix); submit error propagation
- `tests/integration/integration.go` — package clause corrected (`package integration`)
- `internal/testing/production_test.go`, `internal/testing/util/util_test.go` — temp-dir instead of missing `testdata/`

## Commands executed (actual outcomes)

| Command | Result |
| --- | --- |
| `go build ./...` | pass (after repairing the pre-existing broken edit) |
| `go vet ./...` | pass |
| `go test ./... -count=1` | **pass: 86 packages ok, 0 failures** |
| `go test -race ...` | **cannot run**: requires cgo, no C compiler on this machine |
| `go test -run XXX -bench . -benchtime 50x ./model/ ./inference/ ./tensor/math/` | pass; numbers in benchmark-methodology.md |
| `gofmt -l` (module dirs) | clean |

## Acceptance scenario

`tests/integration/d040_acceptance_test.go` runs 9 stages (construct model,
AstroIR representation, validate+optimize, CPU-backend execution vs
autograd, analytic gradients, optimizer convergence, checkpoint restore,
corruption detection, scheduler/cancellation/limits) and writes
`%TEMP%/astrovox-d040-acceptance.json`. It passes.
