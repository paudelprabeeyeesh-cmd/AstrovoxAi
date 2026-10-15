# D-040 Testing Strategy

## Principles

- Kernels are verified against **independent oracles**: naive triple-loop
  GEMM, direct convolution, naive pooling, naive DFT, analytic gradients,
  and central finite differences. A kernel agreeing with itself proves
  nothing.
- Tolerances are per-operation (1e-9..1e-12 for float64 reference checks,
  1e-4 for finite differences with h=1e-6).
- Concurrency tests use deterministic synchronization (WaitGroup, channels,
  barriers) — no `time.Sleep` to hide races.
- Every defect fixed in this work has a regression test named for the
  behavior it pins.

## Coverage added (packages that had zero tests)

- `tensor/math` — the library used by production inference had no test
  files at all. Now: 20 test functions covering GEMM (all transpose combos,
  sizes crossing the 96/256 cache blocks, beta accumulation, error cases),
  conv2d (direct vs im2col vs reference, strided), conv1d, maxpool,
  layernorm/groupnorm forward and backward, RMSNorm, FFT vs DFT + inverse,
  every fused activation (including a non-default leaky slope), fused
  linear/conv/add, BLAS primitives, int8 quantization, empty-tensor
  rejections.
- `tensor/ops` — elementwise/broadcast, unary, new softmax/concat/scalar
  ops, matmul/dot, dtype rejections.
- `tensor/reduce` — all reductions, non-contiguous views (the regression
  class), dtype rejections.
- `tensor/broadcast` — rank-mismatch shape computation (the regression).

## Autograd verification

- Every gradient rule is checked against finite differences of the forward
  function (sigmoid/tanh/relu/exp on a grid) or an analytic value
  (sub/div/scale/mean, matmul adjoints).
- Graph shape cases: diamond (parameter reached through two paths
  accumulates 4x for x²+x²), broadcast gradients, detached branches,
  repeated use of a parameter.
- Failure cases: rule-less node, tape replay, disconnected branch,
  unsupported activation.

## Integration

`tests/integration/d040_acceptance_test.go` is the single end-to-end proof:
a real model, a real graph lowered to TIR, executed on the interpreter and
compared to the autograd engine element-for-element; gradients; optimizer
convergence on a deterministic regression task; checkpoint save/restore
with bit-identical outputs; corruption refusal; 50 concurrent inference
requests; cancellation; resource limits. A JSON summary of all stages is
emitted for machine consumption.

## What is NOT verified here

- **Race detector**: cannot run (no cgo toolchain). Concurrency tests pass
  uninstrumented. This is the single largest verification gap.
- **Fuzzing**: existing fuzz seeds exist for tensor/autograd/model; no
  extended `-fuzz` campaigns were run in this session.
- **GPU paths**: no hardware; simulation only.
- **Python backend TypeScript integration suites**: out of scope for the
  Go mission; not executed.
