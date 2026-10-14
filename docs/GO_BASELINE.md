# Go Engine Baseline

Measured, not reported. Commands and their real output are listed so the
numbers can be reproduced.

## How this was produced

```
go version                 # go1.27.1 windows/amd64
go build ./...             # no output: the whole module compiles
go vet ./...               # no output: no vet findings
go test ./... -count=1     # 80 packages ok, 0 failing
gofmt -l .                 # clean for the main tree
```

## Inventory

| Metric | Value |
|---|---|
| Go version | 1.27.1 |
| Module | `github.com/astrovox/astrovox` |
| Go files (main tree) | 345 |
| Test files | 133 |
| `func Test…` functions | **1749** |
| `func Benchmark…` functions | 33 |
| Packages with passing tests | **80** |
| Packages with failing tests | **0** |
| Packages with no test files | 19 |
| `go build ./...` | clean |
| `go vet ./...` | clean |
| `gofmt -l` (main tree) | clean |

## Suites worth naming

| Suite | Purpose | Where |
|---|---|---|
| Cross-tenant isolation | adversarial: can a caller reach a chunk that is not theirs? | `tests/isolation` |
| Retrieval evals | recall@k, MRR, nDCG over a labelled corpus, plus a regression gate | `internal/evals` |
| Grounding | citation accuracy: supported / uncited / missing / not permitted | `internal/grounding` |
| Hybrid search | BM25 + reciprocal rank fusion, owner-scoped | `internal/retrieval` |
| Model router | capability registry, fallback chains, circuit breakers | `internal/chat` |

The two evals are required CI steps. The retrieval fixture fails its own
sanity test if the vector and keyword paths ever score identically, because
that is the state an eval is in when it has stopped measuring anything.

Measured on the shipped implementation, 10 documents, cutoff 5:

```
vector  recall 0.900  mrr 0.690  ndcg 0.736  misses 1 [cdc]
keyword recall 0.900  mrr 0.800  ndcg 0.821  misses 1 [rotation]
hybrid  recall 1.000  mrr 0.820  ndcg 0.859  misses 0
```

The hybrid recovers the miss the vector path had and the miss the keyword path
had, which is the entire reason to fuse.

At a 200-document corpus, where the cutoff actually matters:

```
k=1   recall@k 0.800  mrr 0.800  ndcg 0.800  misses 4
k=5   recall@k 1.000  mrr 0.868  ndcg 0.899  misses 0
k=20  recall@k 1.000  mrr 0.868  ndcg 0.899  misses 0
k=50  recall@k 1.000  mrr 0.868  ndcg 0.899  misses 0
```

Recall saturates at k=5 while MRR stays at 0.868: the relevant chunk is reached
quickly but 16 of 20 queries rank it below first place. That is a real, measured
weakness, and it is the number a reranker would have to beat.

## The 1,393-test claim

The audit document stated: *"The earlier claim of 1,393 Go test functions
cannot be verified from the current root tree: it contains one .go file and a
Go module only under sdk/go/, rather than a root-level Go module."*

**Both halves of that are wrong**, and this baseline is the evidence:

1. There **is** a root-level Go module: `go.mod` at the repository root
   declaring `github.com/astrovox/astrovox`, with top-level package
   directories `autograd/`, `compiler/`, `graph/`, `kernels/`, `runtime/` and
   `tensor/`, plus `internal/`, `cmd/`, `pkg/` and `tests/`.
2. The real count is **1,749 test functions**, so the original claim
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
