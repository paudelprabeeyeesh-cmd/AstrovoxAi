# D-040 Component Status

Labels: **Implemented and tested** · **Implemented, partially verified** ·
**Experimental** · **Unsupported** · **Blocked** · **Failed validation**

## Tensor core

| Component | Status | Evidence |
| --- | --- | --- |
| dtypes, shapes, storage, views | Implemented and tested | `tensor` tests, boundary/property/fuzz suites, 14 verify scripts |
| `tensor/ops` (elementwise, matmul, dot) | Implemented and tested | New `ops_test.go` vs references; broadcast regression |
| Softmax / Concat / scalar ops | Implemented and tested | New in `ops.go`, covered incl. stability and dim-0 cases |
| `tensor/reduce` | Implemented and tested | New `reduce_test.go`; non-contiguous regression fixed |
| `tensor/math` kernels | Implemented and tested | New `math_test.go` vs naive references + finite differences |
| `tensor/transform` | Implemented, partially verified | Existing tests + new reshape contract tests |

## Differentiation and models

| Component | Status | Evidence |
| --- | --- | --- |
| Reverse-mode tape | Implemented and tested | single-use enforced; disconnected nodes get zero (documented) |
| Gradient rules | Implemented and tested | Add/Sub/Mul/Div/Neg/MatMul/Sum/Mean/Scale/Relu/Sigmoid/Tanh/Exp vs finite differences |
| `Detach` | Implemented and tested | stop-gradient semantics test |
| Optimizers SGD/Adam | Implemented and tested | parameter/step tests; convergence demo in acceptance stage 6 |
| `model` package | Implemented and tested | linear/sequential/MLP/MSE + determinism + flatten tests |
| File checkpoints | Implemented and tested | round-trip, determinism, corruption, truncation, interruption, future-version |

## IR, compiler, execution

| Component | Status | Evidence |
| --- | --- | --- |
| `graph` computational graph | Implemented and tested | executor + optimizer tests (1129 lines) |
| AstroIR (compiler TIR) | Implemented and tested | lowering tests, const-folding equivalence, interpreter pipeline tests |
| TIR interpreter (CPU backend) | Implemented and tested | matrix/gemm/conv/bias/add reduce tests |
| `internal/ir` SSA + passes | Experimental | analyses real; passes are stubs (`toCFG` nil); unused by production |
| Execution planner (`internal/planner`) | Experimental | memory planner works; MTIR planning emits unimplemented opcodes |
| GPU/accelerator backends | Unsupported (as verified hardware paths) | simulation stubs; CPU fallback always used; no hardware verification |

## Runtime and scheduling

| Component | Status | Evidence |
| --- | --- | --- |
| `internal/runtime` pool | Implemented and tested | backpressure/stop/drain semantics tested; stress tests updated |
| `runtime.Engine` + `Session` | Implemented and tested | session stress (10k tasks, 500-deep graphs) |
| `inference.Executor` | Implemented and tested | limits, deadlines, cancellation, backpressure, shutdown, stats |

## Observability / security / CI

| Component | Status | Notes |
| --- | --- | --- |
| Executor + engine counters | Implemented and tested | fixed cardinality, no request-derived labels |
| Race detector | Blocked in this environment | no C toolchain for cgo; see limitations.md |
| Fuzzing | Implemented, partially verified | tensor/autograd/model property suites exist; `go test -fuzz` runs are short |
| CI workflow | Implemented, partially verified | `.github/workflows/` has build/test/vet/security/benchmark gates; not executed here |
