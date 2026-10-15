# D-040 Repository Audit

Audit date: 2026-10-15. Method: full-tree source inspection of every Go
package, exported-API extraction, and verification of claims by running
the code. Python directories exist in the repository but all D-040 work
is Go, per the mission constraint.

## Repository shape

- Module: `github.com/astrovox/astrovox` (root `go.mod`), Go 1.27.1
  (toolchain go1.27.1), ~90 packages, ~250 Go source files plus tests.
- Git: branch `fix/checkpoint-persistence-layernorm` at `afda7dc8`
  (1008 commits ahead of `origin/main`); a working copy worktree exists at
  `.prabeesh/` (untracked machinery, excluded from analysis).

## Core engine (the D-040 surface)

| Area | Package | Status before this work |
| --- | --- | --- |
| Tensor core | `tensor/` (+`ops`, `reduce`, `reshape`, `transpose`, `broadcast`, `iterator`, `memory`) | Real, storage-backed, view/slice/transpose with strides. 15 dtypes. Contiguity checks in `ops`; **missing** in `reduce` (silent wrong results on views). |
| Tensor math | `tensor/math/` | Real kernels (GEMM, conv, norms, FFT, quantize, fusion) used by production inference. **Zero test files**; several incorrect gradients and one kernel that discarded its result. |
| Autograd | `autograd/` | Reverse-mode tape with 5 gradient rules (Add, Mul, Neg, MatMul, Sum); unsupported ops silently skipped. |
| Graph / AstroIR | `graph/`, `compiler/` | Real computational graph + real lowering to the TIR IR + TIR optimizer (const folding, DCE, fusion) + scalar IR interpreter. This is the engine's real IR path. |
| Internal SSA IR | `internal/ir/` + `internal/optimizer/` | Structurally complete graph/SSA with validation and serialization, but **all optimization passes are inert stubs** (DCE/LICM/SCCP/GVN/PRE/IPO/Polyhedral check for a CFG that is never produced) and no production code imports it. |
| Backends | `kernels/`, `internal/backend/` | CPU backend real. Vulkan/RAPID/CPU-X86 headers are judgment-backed dispatch tables, not verified kernels — their own docs say "experimental unity build; ABI not yet validated". cuBLAS/DirectML/ROCm/OpenCL/WebGPU/CUDA are thin CPU-simulation stubs behind build tags (no hardware path compiled on any supported target). |
| Dispatch | `kernels/dispatch.go` + `internal/kernel/` | Duplicated registry/dispatch/autotune subsystems. |
| Runtime / scheduler | `runtime/`, `internal/runtime/` | Real bounded worker pool used by `runtime.Session`. `Scheduler.Submit` panicked on send-after-close and blocked forever when the queue was full. |
| Inference serving | `python-backend/...`, `sdk/go-api/`, `internal/distributed/` | Python backend (fastapi) with rulers/agents; Go SDK is protocol-only, not a serving path. |
| Memory planning | `internal/planner/`, `tensor/memory/` | Real arena/bump allocators, standalone. `internal/planner` cannot execute a graph (MTIR emits unimplemented opcodes). |

## Defects found and fixed during this work

Each had a regression test added; all fixes are in the working tree.

1. `internal/tools/tools.go` — a previous working-tree edit had duplicated a
   `BudgetConfig` method into the middle of `Param.Validate`, breaking the
   build. Repaired; the method is defined once.
2. `internal/tools/agent/agent.go` — an agent-approved tool call was still
   refused by the executor's separate default approver, so approved calls
   were reported as "budget cap". Approval is now decided once at the agent
   layer and installed on the executor, and skips are classified
   (`Result.Reason`) so a refusal is not reported as a cap hit.
3. `tensor/math/fused_act.go` — `FusedConvAct` computed the convolution and
   **discarded the result**, then ran bias+activation over the caller's
   uninitialized `out`.
4. `tensor/math/fused_act.go` — `ActLeakyReLU` hardcoded slope 0.01 and
   ignored the `alpha`/`beta` parameters; `FusedLinearAct`/`FusedAddAct`
   silently passed 5 activation types through unchanged. Slope is now a
   parameter; unsupported activations return `CodeUnimplemented`.
5. `tensor/math/norm.go` — `LayerNormBackward` and `GroupNormBackward`
   accumulated the adjoint with raw `x` instead of the normalized `xHat`,
   and omitted the affine weight `w` from the gradient. Both are now
   verified against central finite differences.
6. `tensor/math/fft.go` — `FFT`/`FFT2` indexed a nil typed view and panicked
   on complex128 input; now a typed error.
7. `tensor/math/quant.go` — three paths indexed `xv[0]` without a length
   check and panicked on empty tensors; now typed errors.
8. `tensor/broadcast/broadcast.go` — `BroadcastShapes` compared dims
   right-aligned but wrote the output left-aligned, so any rank-mismatched
   broadcast produced a **reversed shape** (e.g. `[2,3] + [3] -> [3,2]`).
9. `tensor/reduce/reduce.go` — reductions read the typed view as logical
   data, silently producing wrong results for transposed/sliced views; all
   paths now materialize non-contiguous input first.
10. `tensor/reduce/plan.go` + `reduce.go` — the outer-index mapping used
    input dim indices against the output shape, panicking whenever a reduced
    dim preceded an outer one (reducing dim 0, keepDims or not). The plan
    now carries the input→output dim mapping.
11. `autograd/ops.go` — `Sigmoid` gradient used `y*(1-y^2)` and `Tanh` used
    `y^2-1`-style sign errors; both corrected and verified against finite
    differences.
12. `autograd/ops.go` — `Mul`'s backward **swallowed** the un-broadcast
    error, accumulating a wrongly-shaped gradient.
13. `autograd/autograd.go` — a recorded node with no gradient rule was
    silently skipped (silent zero gradient); now a `CodeUnimplemented`
    error. The tape is single-use: replay is refused instead of
    double-accumulating or differentiating post-optimizer values.
14. `internal/runtime/runtime.go` — `Submit` panicked on send after `Stop`
    closed the channel, and blocked indefinitely when the queue was full.
    Refusals are now typed (`ErrQueueFull`, `ErrSchedulerStopped`);
    `Stop` drains accepted work.
15. `internal/testing`, `internal/testing/util` — golden-file tests wrote to
    relative `testdata/` paths that do not exist; now `t.TempDir()`.
16. `tests/integration/integration_test.go` — hardcoded IR node IDs broke on
    `-count=2` because `ir.AddNode` uses a global counter; uses returned IDs.

## Untested-then-verified areas

`tensor/math`, `tensor/ops`, `tensor/reduce`, and `tensor/broadcast` had no
test files while being used by production inference. All four now have
reference-oracle suites (naive GEMM/conv/pool, analytic gradients, naive
DFT, finite-difference gradient checks).

## Honest gaps (see limitations.md)

- Race detector cannot run here (no C toolchain for cgo).
- `internal/ir`'s optimization passes are stubs; the real IR path is
  `graph -> compiler TIR`.
- GPU backends are not hardware-verified; CPU is the verified backend.
