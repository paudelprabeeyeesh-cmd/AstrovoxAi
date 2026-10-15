# D-040 Backend Contract

## The contract

`internal/backend.Backend` requires, per op: `Supported()`, `Priority()`,
`Name()`, and the kernel (`MatMul`, `Add`, `Sub`, `Scale`, `ReLU`,
`Softmax`, ...). `Supported` depends only on shapes/dtype — not on
measurements — so it stays pure and testable.

## Backend status (verified by code inspection, not by hardware)

| Backend | File | Status |
| --- | --- | --- |
| CPU | `internal/backend/cpu.go` | Real; used as the reference/fallback path |
| Vulkan/RAPID/CPU-X86 | `vulkan.go`, `rapid.go`, `cpu_x86.go` | **Experimental**: judgment-backed dispatch tables, not verified kernels; their own docs state the ABI is unvalidated |
| cuBLAS/DirectML/ROCm/OpenCL/WebGPU/CUDA | respective files | **Simulation**: thin stubs behind build tags; no hardware path compiles on supported targets |

## Rules asserted by this contract

1. A backend reports capabilities, not intentions. If it cannot run an op
   for the given shapes/dtype, `Supported` is false.
2. `Compile` returns `[]backend.CompiledKernel`; the executor must check
   every kernel is non-nil, or fail — it never silently substitutes a
   different kernel. (Verified by a regression test.)
3. Selection prefers higher priority among supporting backends; CPU is
   the always-available fallback (`internal/backend/selector_test.go`).
4. Cancellation is checked at safe boundaries between kernels.

## Honest statement

No accelerator backend in this repository is hardware-verified. CPU tests
and backend-independent contract tests are what can run here. The existing
`docs/d040/backend-contract.md` states the same; this entry records that
the situation is unchanged by the current work.
