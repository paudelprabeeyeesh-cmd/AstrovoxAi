# ASTROVOX AI — MISSION D-042 TESTING DOCUMENTATION

**Date:** 2026-10-16  
**Repository:** `github.com/astrovox/astrovox`  
**Language:** Go (go 1.27)

---

## 1. Test Philosophy

Every confirmed defect is fixed with a regression test before the fix is merged. Tests verify real behavior against independent oracles, not just API shape. No test is skipped, disabled, or weakened to achieve a green build.

## 2. Test Categories

| Category | Location | Description |
| --- | --- | --- |
| Unit tests | `*_test.go` alongside each package | Individual functions and methods |
| Regression tests | `*_test.go` | One per confirmed defect (see defect log) |
| Contract tests | `tests/integration/d042_contract_test.go` | Cross-package behavior contracts |
| Acceptance test | `tests/integration/d042_acceptance_test.go` | End-to-end clean-checkout scenario |
| Fuzz tests | `fuzz_test.go` in `tensor/`, `tensor/broadcast/`, `internal/checkpoint/` | Malformed-input resilience |
| Benchmarks | `bench_test.go` | Performance baselines |

## 3. Contract Tests (`tests/integration/d042_contract_test.go`)

| Test | What it verifies |
| --- | --- |
| `TestContractCheckpointRoundTrip` | WriteFile → ReadFile → Inspect round-trip fidelity |
| `TestContractCheckpointCorruptionIsRefused` | Single-bit corruption → `CodeCorruptData` |
| `TestContractCheckpointFutureVersionIsRefused` | Newer format → `CodeVersionMismatch` |
| `TestContractInferenceDeadlineRefused` | Expired deadline → `CodeTimeout` at submission |
| `TestContractInferenceResourceLimitRefused` | Oversized input → `CodeResourceExhausted` |
| `TestContractModelDeterminism` | Same seed/shape → bit-identical parameters |
| `TestContractFlattenRejectsSharedParameter` | Duplicate parameter → error |
| `TestContractAutogradRulelessNodeErrors` | Rule-less op → `CodeUnimplemented` |

## 4. Acceptance Test (`tests/integration/d042_acceptance_test.go`)

The clean-checkout acceptance test exercises 15 stages:

1. Build
2. Validate configuration
3. Create deterministic model (MLP 2→4→1)
4. Real forward pass
5. Gradient computation (finite-difference verified)
6. Training pipeline (loss decrease measured)
7. Save checkpoint (atomic, versioned)
8. Restore into fresh model (bit-identical outputs)
9. Compile and execute AstroIR graph
10. Optimized vs reference execution
11. Concurrent inference (30 requests)
12. Cancellation + resource limits
13. Workflow recovery (reported as skipped — not implemented)
14. Machine-readable acceptance report

The acceptance report is written as JSON to the test temp directory.

## 5. Fuzz Tests

| Target | Package | What it fuzzes |
| --- | --- | --- |
| `FuzzParseDType` | `tensor` | DType parser never panics |
| `FuzzLoad` | `tensor` | Tensor deserialization never panics |
| `FuzzNewShape` | `tensor` | Shape validation never panics |
| `FuzzArange` | `tensor` | Arange never panics |
| `FuzzBroadcastShapes` | `tensor/broadcast` | BroadcastShapes never panics |
| `FuzzCheckpointDecode` | `internal/checkpoint` | Checkpoint reader never panics |

## 6. Test Commands

```bash
# Full test suite
go test ./... -count=1

# Specific package
go test ./tensor/math/ -count=1 -v

# Race detector (requires cgo toolchain; blocked in this environment)
go test -race ./tensor/...

# Benchmarks
go test -run XXX -bench . -benchtime 50x ./model/ ./inference/ ./tensor/math/

# Acceptance test
go test ./tests/integration/ -run TestD042Acceptance -count=1 -v

# Contract tests
go test ./tests/integration/ -run TestContract -count=1 -v
```

## 7. Race Detection Status

The race detector **cannot run** in this environment — Go's `-race` requires cgo and a C compiler (`gcc`), which is not installed on this Windows host. All concurrency tests pass uninstrumented. CI must run `-race` on a runner with a working C toolchain.

## 8. Coverage

Coverage is collected via `go test -cover ./...`. Critical paths (tensor math, autograd backward, checkpoint read/write, inference executor) have dedicated test coverage. No critical path is entirely untested.
