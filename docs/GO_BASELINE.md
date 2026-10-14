# Go Engine Baseline

Measured, not reported. Commands and their real output are listed so the
numbers can be reproduced.

## How this was produced

```
go version          # go1.27.1 windows/amd64
go build ./...      # no output: the whole module compiles
go vet ./...        # no output: no vet findings
go test ./... -count=1 -short -cover
```

## Inventory

| Metric | Value |
|---|---|
| Go version | 1.27.1 |
| Module | `github.com/astrovox/astrovox` |
| Go files (main tree) | 333 |
| Test files | 127 |
| `func Test…` functions | **1661** |
| `func Benchmark…` functions | 33 |
| Packages with passing tests | **77** |
| Packages with failing tests | **0** |
| Packages with no test files | 19 |
| `go build ./...` | clean |
| `go vet ./...` | clean |

## The 1,393-test claim

The audit document stated: *"The earlier claim of 1,393 Go test functions
cannot be verified from the current root tree: it contains one .go file and a
Go module only under sdk/go/, rather than a root-level Go module."*

**Both halves of that are wrong**, and this baseline is the evidence:

1. There **is** a root-level Go module: `go.mod` at the repository root
   declaring `github.com/astrovox/astrovox`, with top-level package
   directories `autograd/`, `compiler/`, `graph/`, `kernels/`, `runtime/` and
   `tensor/`, plus `internal/`, `cmd/`, `pkg/` and `tests/`.
2. The real count is **1,661 test functions**, so the original claim
   understated the suite rather than overstating it.

`sdk/go/` is a separate module with 9 `.go` files; it is the SDK, not the
engine.

## Coverage (selected)

| Package | Coverage |
|---|---|
| `internal/api/capability` | 98.5% |
| `internal/api/logging` | 97.4% |
| `internal/agents` | 87.4% |
| `internal/api/config` | 85.5% |
| `internal/api/idempotency` | 89.6% |
| `compiler` | 81.1% |
| `autograd` | 70.5% |
| `graph` | 67.8% |
| `cmd/api` | 64.9% |
| `cmd/astrovox` | 47.7% |
| `internal/ai` | 17.7% |
| `cmd/capability` | 0.0% |

## Reproduce

```bash
go build ./...
go vet ./...
go test ./... -count=1
go test ./... -count=1 -short -cover
```

## Not verified here

- **K-001, the benchmark against vLLM and llama.cpp, has not been run.** It
  needs a real open-weight model, representative workloads and comparable
  hardware. No throughput, latency, memory or perplexity numbers are claimed
  anywhere in this repository, and none should be inferred from the tests
  passing. The 33 `Benchmark…` functions in this tree measure the Go runtime
  and tensor operations, not the engine against vLLM or llama.cpp.
- No claim is made that this engine is competitive. An ADR choosing adopt,
  wrap or stop investing requires the measurement above.
