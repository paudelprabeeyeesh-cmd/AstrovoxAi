# ASTROVOX MASTER IMPLEMENTATION CHECKLIST

| Field | Value |
|---|---|
| Source | ASTROVOX MASTER ROADMAP (Version 1.0) |
| Scope | Phase 0 → Phase 23 (24 phases, 229 modules/sub-modules) |
| Audience | High-seniority systems engineering team (Principal/Staff level) |
| Standard | Production-grade HPC, compiler-grade IR, distributed-systems correctness |
| Execution Order | Strictly sequential Phase 0 → 23; no phase may commence until prior phase milestones are met |

**Legend**
- `- [ ]` = incomplete engineering directive
- Every module carries three blocks: **Sub-tasks** (atomic), **Requirements & Constraints**, **Milestones (DoD)**

---

## PHASE 0 — FOUNDATION (11 modules)

### 0.1 Project Architecture [x]
**Engineering Sub-tasks:**
- [ ] Define the four-layer architecture boundary: `kernel/backend → tensor/math → compiler/runtime → service/API`
- [ ] Codify dependency-inversion rules: no upward imports; enforce via `depguard`/`go vet`/`ruff` import-linter rules
- [ ] Specify the internal package contract surface (`internal/` root, unexported symbols, stable public API in `pkg/`)
- [ ] Establish the cross-language boundary: Go engine core, Python SDK facade, FFI shim specification
- [ ] Document the concurrency model per layer (data-parallel, task-parallel, async I/O) and the failure-domain isolation strategy
- [ ] Produce the ADR-0000 architecture baseline with component interaction diagrams (C4 level 2/3)

**Implementation Requirements & Constraints:**
- Layered architecture must permit zero-cost abstraction at the tensor layer; no virtual dispatch on hot paths
- Public API must be semantically versioned; internal packages are exempt from stability guarantees
- Architecture decision records are mandatory for any cross-layer interface change

**Engineering Milestones (DoD):**
- [ ] C4 diagrams + ADR-0000 merged; dependency-linter CI gate passes on 100% of packages
- [ ] Layering violation count = 0 in `internal/` per static analysis

### 0.2 Repository Layout [x]
**Engineering Sub-tasks:**
- [ ] Define canonical tree: `cmd/`, `internal/{ir,optimizer,planner,scheduler,runtime,backend,kernel,planner,rewrite,tools}`, `pkg/{cli,sdk}`, `astrovox/` (Python), `tests/{unit,integration,e2e}`, `testdata/`, `docs/`, `scripts/`
- [ ] Enforce `internal/` visibility: engine internals unimportable from `pkg/` consumers
- [ ] Standardize file naming: `snake_case.go`, one type per file for exported types, `_test.go` colocated
- [ ] Configure `.gitignore` for build artifacts, `.astrovox/` local state, `__pycache__`, coverage output
- [ ] Establish `testdata/` golden-file conventions (checksum-verified, deterministic generation)

**Implementation Requirements & Constraints:**
- Go module path `github.com/astrovox/astrovox`; Python package `astrovox` mirrors engine semantics
- Layout must support monorepo CI: per-package `go test` shards and per-module pytest shards

**Engineering Milestones (DoD):**
- [ ] `go build ./...` clean from repo root; `pytest --collect-only` returns expected test count
- [ ] Golden-file checksum manifest committed; layout lint passes in CI

### 0.3 Module System [x]
**Engineering Sub-tasks:**
- [ ] Define module interfaces: every module exposes an explicit `Module`/`Init()`/`Shutdown()` lifecycle contract
- [ ] Implement dependency injection container with constructor-level dependency graphs and cycle detection
- [ ] Establish module registry (name → factory) with duplicate-registration panic semantics
- [ ] Specify version-gated module loading: modules declare `MinEngineVersion`/`MaxEngineVersion`
- [ ] Implement module-level feature flags and capability negotiation between modules

**Implementation Requirements & Constraints:**
- Module initialization must be deterministic and idempotent; double-init returns `ErrAlreadyInitialized`
- No global mutable state outside the registry; all cross-module access through interfaces

**Engineering Milestones (DoD):**
- [ ] 100% of modules implement lifecycle contract; cycle-detection unit test with 100+ node graph
- [ ] Module load failure of any single module degrades to clean `ErrModuleUnavailable`, never panic

### 0.4 Error Package [x]
**Engineering Sub-tasks:**
- [ ] Define typed error taxonomy: `ErrInvalidArgument`, `ErrOutOfRange`, `ErrShapeMismatch`, `ErrDTypeMismatch`, `ErrDeviceUnavailable`, `ErrOutOfMemory`, `ErrTimeout`, `ErrCancelled`, `ErrInternal`
- [ ] Implement error wrapping with `errors.Is`/`errors.As` compatibility and stack-frame capture (1 frame minimum)
- [ ] Build error code registry (stable integer codes per error class) for wire/CLI stability
- [ ] Implement structured error context: `WithField(key, value)`, `WithOperation(op)`, redaction hooks for secrets
- [ ] Define sentinel vs. dynamic error policy; error-message internationalization skeleton

**Implementation Requirements & Constraints:**
- Hot-path error construction must be allocation-light (lazy message formatting)
- Error codes are API-stable: never reuse or renumber a retired code

**Engineering Milestones (DoD):**
- [ ] 100% of exported functions return typed errors; zero bare `errors.New` outside the error package
- [ ] Error-path coverage ≥ 90% in core packages; fuzz test on error-wrapping round-trips

### 0.5 Logger [x]
**Engineering Sub-tasks:**
- [ ] Implement leveled structured logger (`Debug/Info/Warn/Error/Fatal`) with JSON + console sinks
- [ ] Build field-based context propagation (`WithFields`) across goroutines/tasks without data races
- [ ] Implement asynchronous buffered sink with backpressure policy (drop-oldest vs. block, configurable)
- [ ] Add per-module log filtering, sampling for high-frequency events, and PII/secret redaction filters
- [ ] Wire log correlation IDs into task/request spans for distributed tracing readiness

**Implementation Requirements & Constraints:**
- Logger must be lock-free on the hot path (ring buffer); worst-case serialization cost < 1 µs per entry
- `Fatal` must flush before `os.Exit(1)`; no log loss on crash paths

**Engineering Milestones (DoD):**
- [ ] Throughput benchmark ≥ 1M entries/sec on ring buffer; zero data races under `-race`
- [ ] 100% of modules use structured logger; zero `fmt.Println`/`print` in non-test code

### 0.6 Configuration [x]
**Engineering Sub-tasks:**
- [ ] Implement layered config: defaults → file (YAML/TOML) → environment → CLI flags (precedence defined)
- [ ] Define typed config schema with validation rules (range, enum, required) and JSON Schema export
- [ ] Implement hot-reloadable config sections with watcher (fsnotify/inotify) and rollback-on-invalid
- [ ] Build secret injection path: config keys resolve from secret manager without persisting plaintext
- [ ] Add config snapshot/diff tooling for audit and drift detection

**Implementation Requirements & Constraints:**
- Config reads after startup must be lock-free (atomic pointer swap on reload)
- All config keys namespaced `astrovox.<section>.<key>`; env mapping `ASTROVOX_<SECTION>_<KEY>`

**Engineering Milestones (DoD):**
- [ ] Config validation rejects 100% of invalid schemas in fuzz test; reload applies in < 50 ms p99
- [ ] Zero secret leakage in config dump output (redaction test with synthetic secrets)

### 0.7 Build System [x]
**Engineering Sub-tasks:**
- [ ] Define Go build matrix: Go 1.22+/1.23+ targets, CGO toggle, `-tags simd,gpu,debug`
- [ ] Implement reproducible builds: pinned toolchains, locked dependency hashes (`go.sum`, `requirements.lock`)
- [ ] Configure build cache strategy (GOCACHE/GOMODCACHE, CI cache keys by lockfile hash)
- [ ] Add build profiling (`-pgo`, pprof) and cross-compilation targets (linux/amd64, linux/arm64, darwin, windows)
- [ ] Integrate SBOM generation (Syft/cyclonedx) and supply-chain attestation (cosign/SLSA provenance)

**Implementation Requirements & Constraints:**
- Clean-room build must succeed with network disabled after module download
- Build artifacts carry version, commit SHA, and build timestamp via `-ldflags`

**Engineering Milestones (DoD):**
- [ ] Reproducible build bit-identical across two clean runs on same toolchain
- [ ] Full matrix builds in CI ≤ 15 min; SBOM + provenance attached to every release artifact

### 0.8 Version Manager [x]
**Engineering Sub-tasks:**
- [ ] Implement semantic versioning engine: `MAJOR.MINOR.PATCH[-prerelease][+build]`
- [ ] Define version compatibility matrix (engine ↔ SDK ↔ plugins ↔ IR format versions)
- [ ] Build version comparison/constraint resolver (`^1.2.0`, `>=2.0.0 <3.0.0`) for module resolution
- [ ] Implement runtime version reporting endpoint (`astrovox version --json`) with Git SHA, build date, Go/Python versions
- [ ] Add upgrade-path checker: validates config/IR/checkpoint compatibility against target version

**Implementation Requirements & Constraints:**
- IR serialization format version is independent of engine version; migrations must be forward+backward compatible within one MAJOR
- Version numbers never fabricated; derived from VCS tags at build time

**Engineering Milestones (DoD):**
- [ ] Constraint resolver passes 10k-case property test; version endpoint returns deterministic JSON schema
- [ ] Upgrade checker detects 100% of breaking changes in a synthetic version-jump suite

### 0.9 Benchmark Framework [x]
**Engineering Sub-tasks:**
- [ ] Integrate `go test -bench` + `benchstat` for statistical rigor; pytest-benchmark for Python layer
- [ ] Define benchmark taxonomy: micro (per-op), macro (end-to-end pipeline), soak (duration)
- [ ] Implement fixed-workload harness: seeded RNG, warmup iterations, GC control, CPU pinning
- [ ] Build regression gate: compare against `docs/performance-baseline.md` with p-value thresholds
- [ ] Add benchmark artifact storage (JSON + flamegraph) per CI run

**Implementation Requirements & Constraints:**
- Benchmarks must report ns/op, allocs/op, B/op; timer excludes setup
- Environment metadata (CPU, frequency, cache topology) recorded per run

**Engineering Milestones (DoD):**
- [ ] ≥ 100 micro-benchmarks covering every tensor op; CI fails on > 5% p95 regression vs. baseline
- [ ] Benchmark variance (CoV) < 3% across 10 repeated runs on pinned hardware

### 0.10 Testing Framework [x]
**Engineering Sub-tasks:**
- [ ] Establish test pyramid targets: unit ≥ 70%, integration ≥ 20%, e2e ≤ 10%
- [ ] Build shared test utilities: deterministic RNG seeds, temp-dir fixtures, golden-file helpers, assertion DSL
- [ ] Implement test isolation: per-test working dirs, no cross-test globals, `-race` + `-count=1` defaults
- [ ] Wire coverage instrumentation with per-package gates and coverage profile aggregation
- [ ] Define flaky-test policy: quarantine list with 48h SLA, auto-retry limit = 2, failure triage runbook

**Implementation Requirements & Constraints:**
- All tests hermetic: no network, no clock dependency (injectable clock), no filesystem outside temp dirs
- Unit tests must run without elevated privileges or GPU

**Engineering Milestones (DoD):**
- [ ] Coverage ≥ 85% on `internal/ir`, `internal/optimizer`, `internal/runtime`; ≥ 70% repo-wide
- [ ] Flaky-test rate < 0.5% over 1000 CI runs; full unit suite executes ≤ 5 min

### 0.11 Documentation Structure [x]
**Engineering Sub-tasks:**
- [ ] Define docs taxonomy: `docs/` = reference, `docs/adr/` = decisions, `docs/tutorials/` = guided, `docs/api/` = generated
- [ ] Configure doc generation: GoDoc/pkd for Go, Sphinx/pdoc for Python, OpenAPI spec from route handlers
- [ ] Establish doc-lint rules: every exported symbol has a doc comment; examples compile as tests
- [ ] Implement versioned docs: per-release snapshots, `latest` symlink, redirect map for moved pages
- [ ] Add docs CI: link checking, spell check, Markdown lint, diagram build (Mermaid/d2)

**Implementation Requirements & Constraints:**
- Docs live in the same repo as code; doc changes reviewed with the code change (docs-as-code)
- Generated docs are never hand-edited; regeneration is part of release pipeline

**Engineering Milestones (DoD):**
- [ ] 100% exported symbols documented; docs CI green; every tutorial executes end-to-end in a clean env
- [ ] Doc build ≤ 2 min; versioned docs available for the last 3 releases

---

## PHASE 1 — MATH CORE / LINEAR ALGEBRA (19 modules)

### 1.1 Vector [x]
**Engineering Sub-tasks:**
- [ ] Implement `Vector[T]` typed contiguous buffer with stride, offset, and capacity semantics
- [ ] Implement elementwise ops: `Add`, `Sub`, `Mul`, `Div`, `Neg`, `Scale`, `Dot`, `Norm(L1/L2/Linf)`, `Axpy`
- [ ] Implement comparisons and reductions: `Equal` (tolerance-based), `Min`, `Max`, `ArgMin`, `ArgMax`, `Sum`, `Mean`
- [ ] Implement `Concat`, `Slice`, `Copy`, `Fill`, `Zero`, `Clone` with bounds-checked indexing
- [ ] Implement iterator protocol for cache-friendly traversal and `fmt.Stringer`/JSON marshaling

**Implementation Requirements & Constraints:**
- All ops must be O(n) single-pass unless stated; no hidden allocations in arithmetic paths
- Generic over `float32`, `float64`, `int32`, `int64`; NaN/Inf propagation per IEEE 754

**Engineering Milestones (DoD):**
- [ ] ≥ 40 unit tests incl. edge cases (empty, length-1, denormals, ±Inf, NaN)
- [ ] Dot product ≥ 8 GFLOP/s scalar baseline on AVX2 host; benchmarks for every op

### 1.2 Matrix [x]
**Engineering Sub-tasks:**
- [ ] Implement `Matrix[T]` with row-major layout, leading-dimension (LD) parameter for submatrix views
- [ ] Implement `MatMul` (naive + tiled), `Transpose`, `Add`, `Scale`, `Hadamard`, `Trace`, `Determinant`, `Inverse` (LU), `Solve`
- [ ] Implement row/column extraction, `RowSwap`, `RowReduce`, `Rank` (SVD-free tolerance rank), `Norm` (Frobenius, nuclear)
- [ ] Implement block partitioning and `Submatrix` zero-copy views with bounds validation
- [ ] Implement serialization (row-major binary + header) and `Equal` with ULP tolerance

**Implementation Requirements & Constraints:**
- MatMul must call BLAS when available (`cgo` dgemm/sgemm) with pure-Go fallback
- LU decomposition must use partial pivoting; singular matrices return `ErrSingularMatrix`

**Engineering Milestones (DoD):**
- [ ] Inverse/Solve verified against reference implementation on 100 random matrices (n ≤ 512), rel. error < 1e-9 (float64)
- [ ] Tiled MatMul ≥ 70% of OpenBLAS DGEMM on same hardware; cache-block size auto-tuned per L2

### 1.3 Tensor [x]
**Engineering Sub-tasks:**
- [ ] Implement `Tensor` N-dimensional container: shape, strides, dtype, device, layout tag, data pointer
- [ ] Implement constructor set: `New`, `Zeros`, `Ones`, `Full`, `Arange`, `Linspace`, `Eye`, `Random` (seeded)
- [ ] Implement elementwise unary/binary ops with broadcasting dispatch
- [ ] Implement `Reshape`, `Flatten`, `ExpandDims`, `Squeeze`, `Cast` (dtype conversion with saturation policy)
- [ ] Implement deep equality (shape + dtype + values within tolerance) and `String()` pretty-printer for rank ≤ 4

**Implementation Requirements & Constraints:**
- Tensor must support non-contiguous strides (views) without copy; ops on views must materialize lazily or copy explicitly
- Dtype registry: `float16/32/64`, `bfloat16`, `int8/16/32/64`, `uint8/16/32/64`, `bool`, `complex64/128`

**Engineering Milestones (DoD):**
- [ ] ≥ 120 unit tests across dtypes/ranks 0–8; zero-copy view tests verify no allocation via `testing.AllocsPerRun`
- [ ] Constructor benchmarks: 1M-element `Random` < 5 ms; `Zeros` page-aligned

### 1.4 Sparse Tensor [x]
**Engineering Sub-tasks:**
- [ ] Implement COO (coordinate) format: `indices [N, ndims]`, `values [N]`, shape, `Canonicalize` (sorted, deduped)
- [ ] Implement CSR/CSC conversion with `ToCSR`, `ToCSC`, format validation, and `NNZ` accessor
- [ ] Implement sparse-dense ops: `SparseToDense`, `DenseToSparse` (threshold), `SpMV`, `SpMM`, `Add` (sparse+sparse)
- [ ] Implement storage compression (index delta encoding) and slicing on leading dimension
- [ ] Implement sparsity profiling: density report, fill ratio, op-cost estimator

**Implementation Requirements & Constraints:**
- COO must be canonical (row-major lexicographic) before arithmetic; duplicates merge by summation
- SpMV must exploit CSR row pointers for O(NNZ) traversal; no dense intermediate materialization

**Engineering Milestones (DoD):**
- [ ] SpMV matches dense reference within 1e-6 rel. error on 10k random sparse matrices (density 0.1%–5%)
- [ ] Memory footprint ≤ 16 bytes/NNZ (float32); `DenseToSparse` at 90% density degrades gracefully with warning

### 1.5 Dense Tensor [x]
**Engineering Sub-tasks:**
- [ ] Implement contiguous dense storage with allocator hook (arena/pool injection point)
- [ ] Implement `StridesFor(shape)` computation (row-major, column-major, channel-last variants)
- [ ] Implement zero-copy `AsView`, `Contiguous` (copy-to-contiguous), `Detach` (storage decouple)
- [ ] Implement `SetStorage`, `ShareStorageWith` aliasing control and alias detection
- [ ] Implement memory-budget-aware construction: pre-flight capacity check against `BudgetChecker`

**Implementation Requirements & Constraints:**
- Dense tensor data must be 64-byte aligned for SIMD; allocator enforces alignment
- Aliasing writes must be explicit: `ShareStorageWith` marks tensors as mutually mutable

**Engineering Milestones (DoD):**
- [ ] Stride computation correct for 10k random shapes; alignment assertion holds on 1M allocations
- [ ] Zero-copy operations show 0 B/op in `testing.AllocsPerRun`; pre-flight OOM check blocks 100% of over-budget allocations in fault-injection test

### 1.6 Tensor Iterator [x]
**Engineering Sub-tasks:**
- [ ] Implement `TensorIterator` broadcasting engine: shape reconciliation, dim-size-1 expansion, stride-0 semantics
- [ ] Implement iteration plans: contiguous fast path, tiled iteration for cache locality, parallel split points
- [ ] Implement `Iter`, `IterConst`, `ForEach` with callback vectorization hints
- [ ] Implement reduction iterator: dim-masked traversal with accumulation buffers per thread
- [ ] Implement iterator invalidation rules and re-entrancy guards

**Implementation Requirements & Constraints:**
- Iterator must fuse broadcast+op into single pass; no intermediate broadcast materialization
- Parallel split only when `numel/threads ≥ 4096` to amortize spawn cost

**Engineering Milestones (DoD):**
- [ ] Broadcasting correctness on 500 shape permutations vs. NumPy reference (deterministic seed)
- [ ] `ForEach` achieves ≥ 90% of hand-written loop throughput; tiling benchmark shows ≤ 5% L2 miss rate on 4K×4K float32

### 1.7 Tensor Views [x]
**Engineering Sub-tasks:**
- [ ] Implement zero-copy views: `ReshapeView`, `TransposeView`, `SliceView`, `ExpandView`, `AsStrided`
- [ ] Implement view-chain tracking (`view_graph`) for autograd provenance and `Base` resolution
- [ ] Implement writability rules: views sharing storage with overlapping regions must be write-safe or flagged
- [ ] Implement `Materialize` (copy-on-write trigger) and view-lifetime extension of base storage
- [ ] Implement view diagnostics: `IsView`, `StorageOffset`, `Overlaps(other)`

**Implementation Requirements & Constraints:**
- Views must never own memory; base tensor lifetime must dominate all derived views (refcounted storage)
- `AsStrided` validates bounds for every index in the view extent before returning

**Engineering Milestones (DoD):**
- [ ] 100% of view ops are zero-allocation (`AllocsPerRun == 0`); overlap detector passes 1k adversarial cases
- [ ] Use-after-free impossible by construction: storage refcount test with forced GC cycles

### 1.8 Tensor Broadcasting [x]
**Engineering Sub-tasks:**
- [ ] Implement broadcast rule engine: right-align shapes, dim-1 expansion, error on mismatch ≠ 1
- [ ] Implement `BroadcastShapes(shapeA, shapeB)` pure function with detailed mismatch diagnostics
- [ ] Implement broadcast-aware `Strides` computation producing stride-0 virtual expansion
- [ ] Implement broadcasting in all binary elementwise ops and reduction keepdim semantics
- [ ] Implement scalar broadcasting (rank-0) and mixed-dtype promotion rules

**Implementation Requirements & Constraints:**
- Broadcasting must never allocate the expanded tensor; stride-0 handles expansion
- Dtype promotion follows a fixed lattice (int→uint→float→complex), no silent precision loss

**Engineering Milestones (DoD):**
- [ ] `BroadcastShapes` validated against 10k NumPy-equivalent cases including failure cases (error message must name offending dim)
- [ ] Broadcast add on (1024,1)+(1,1024) allocates only output buffer (0 extra B/op)

### 1.9 Tensor Indexing [x]
**Engineering Sub-tasks:**
- [ ] Implement index types: integer, slice, ellipsis, `NewAxis`, boolean mask, integer-array (advanced)
- [ ] Implement `Get(index...)`/`Set(value, index...)` with mixed basic/advanced indexing semantics
- [ ] Implement advanced indexing: multi-array broadcast of indices, result-shape computation, scatter
- [ ] Implement boolean-mask `Where`, `NonZero`, `MaskedSelect`, `Count`
- [ ] Implement negative-index normalization and out-of-range panic/`ErrIndexOutOfRange` policy

**Implementation Requirements & Constraints:**
- Advanced indexing with N index arrays must produce copy semantics (not views) matching NumPy rules
- Boolean mask ops must be single-pass over `numel` with prefix-sum for output sizing

**Engineering Milestones (DoD):**
- [ ] Indexing semantics verified against NumPy on 500 mixed-index cases (seeded)
- [ ] `NonZero` on 1M-element tensor < 3 ms; `Set` bounds-check overhead ≤ 2 ns/element

### 1.10 Tensor Slicing [x]
**Engineering Sub-tasks:**
- [ ] Implement `Slice(begins, ends)` per-dimension with clamp/validate semantics
- [ ] Implement `StridedSlice(begins, ends, strides)` supporting negative strides (reverse views)
- [ ] Implement `Split(num_or_sections, dim)`, `Chunk`, `VSplit`, `HSplit` with remainder policy
- [ ] Implement `Gather(dim, indices)` and `Scatter(dim, indices, values)` for axis-oriented selection
- [ ] Implement slice → view promotion rules (when slice is a view vs. requires copy)

**Implementation Requirements & Constraints:**
- All slicing ops with step ±1 must return zero-copy views; negative stride permitted on views
- `Scatter` must detect and handle overlapping indices deterministically (documented order)

**Engineering Milestones (DoD):**
- [ ] Slicing matches NumPy on 300 shape/stride permutations; negative-stride view is zero-allocation
- [ ] `Gather` throughput ≥ 500M elements/sec (float32, contiguous indices); overlap test asserts deterministic result

### 1.11 Tensor Reshape [x]
**Engineering Sub-tasks:**
- [ ] Implement `Reshape(shape)` with `-1` inference, zero-preserving semantics, and contiguity check
- [ ] Implement `Flatten(start_dim, end_dim)`, `View` (strict no-copy), and `ReshapeAs(other)`
- [ ] Implement reshape failure path: automatic `Contiguous()` fallback with explicit copy accounting
- [ ] Implement shape-inference helpers: `InferReshapeShape(old, new)` pure function with error taxonomy
- [ ] Implement reshape interaction with autograd (gradient reshape back to input shape)

**Implementation Requirements & Constraints:**
- `Reshape` must be zero-copy when strides permit; otherwise returns a copy and marks storage change
- Total element count must be invariant; `-1` permitted in exactly one position

**Engineering Milestones (DoD):**
- [ ] `InferReshapeShape` property-tested over 10k shape pairs; zero-copy success rate ≥ 95% on random valid reshapes
- [ ] Reshape of 100M-element tensor: zero-copy < 1 µs, copy path bandwidth ≥ 10 GB/s

### 1.12 Tensor Transpose [x]
**Engineering Sub-tasks:**
- [ ] Implement `Transpose(dim0, dim1)` as stride-swap view
- [ ] Implement general `Permute(dims)` with validation (permutation completeness, bounds)
- [ ] Implement `T` (rank-2 shortcut), `MoveAxis`, `SwapAxes`, `Flip(dims)`
- [ ] Implement `ContiguousTranspose` (blocked tiling transpose for cache efficiency) for materialized copy
- [ ] Implement matmul auto-transpose fusion: detect AᵀB patterns and select transposed GEMM path

**Implementation Requirements & Constraints:**
- Transpose view must be zero-allocation; materialized transpose must use cache-block tiling (block ≤ L2/3)
- `Permute` must reject non-bijective dimension lists with per-dim diagnostics

**Engineering Milestones (DoD):**
- [ ] Transpose views zero-alloc across 1k cases; tiled transpose ≥ 20 GB/s on 4096×4096 float32 (≥ 80% of memcpy-equivalent)
- [ ] Matmul fusion benchmark: AᵀB path avoids explicit transpose (0 intermediate allocation)

### 1.13 Tensor Reduction [x]
**Engineering Sub-tasks:**
- [ ] Implement `Sum`, `Mean`, `Var`, `Std`, `Min`, `Max`, `Prod`, `Norm`, `All`, `Any` over arbitrary dims
- [ ] Implement `keepdim` semantics and multi-dim reduction with sequential-dim fusion
- [ ] Implement parallel reduction tree (per-thread partials, log(N) combine) with associative-order error bounds
- [ ] Implement `ArgMin`/`ArgMax` (value+index, tie-breaking = first occurrence), `CumSum`, `CumProd`
- [ ] Implement numerically stable variants: `LogSumExp`, `Welford` variance, `softmax-safe` max-subtract

**Implementation Requirements & Constraints:**
- Floating-point reduction order must be deterministic per-thread-count for reproducibility
- Welford algorithm mandatory for variance/STD to avoid catastrophic cancellation

**Engineering Milestones (DoD):**
- [ ] Reduction results within 2 ULP of pairwise-reference on 100 random tensors per op; Welford vs. naive variance test on high-magnitude data shows rel. error < 1e-7 vs. > 1e-2
- [ ] Parallel sum on 100M float32 ≥ 15 GFLOP/s effective; `LogSumExp` stable on inputs offset by ±1000

### 1.14 Tensor Validation [x]
**Engineering Sub-tasks:**
- [ ] Implement `ValidateShape` (rank limits, dim-size bounds, zero-dim policy)
- [ ] Implement `ValidateDType` (op-dtype matrix: which ops accept which dtypes)
- [ ] Implement `ValidateDevice` (tensor device vs. op-required device), `ValidateLayout` (contiguity requirements)
- [ ] Implement `ValidateFinite` (NaN/Inf scan), `ValidateRange` (min/max bounds for int/uint casts)
- [ ] Implement composite `AssertCompatible(a, b, op)` pre-flight check used by all binary ops

**Implementation Requirements & Constraints:**
- Validation must be O(1) except `ValidateFinite` (O(n), SIMD-accelerated, skip-able in release builds via flag)
- All validation errors carry shape/dtype/device context in structured fields

**Engineering Milestones (DoD):**
- [ ] Validation layer rejects 100% of malformed op inputs in a 5k-case adversarial suite; zero false positives on valid set
- [ ] `ValidateFinite` on 100M float32 < 8 ms (SIMD); validation overhead on hot path < 1% (benchmark-verified)

### 1.15 Tensor Profiler [x]
**Engineering Sub-tasks:**
- [ ] Implement per-op instrumentation: dtype, shape, device, duration, bytes-read, bytes-written, FLOPs
- [ ] Build op-profile recorder with ring buffer (configurable depth) and low-overhead timestamping (monotonic clock)
- [ ] Implement aggregation: per-op-type p50/p95/p99, throughput (elements/sec), arithmetic intensity
- [ ] Implement `Profile(fn)` scope API plus manual `StartSpan`/`EndSpan` for nested regions
- [ ] Implement export: JSON/Chrome-trace format, per-op table report, flamegraph-compatible stack samples

**Implementation Requirements & Constraints:**
- Profiler overhead must be < 50 ns/op when enabled, 0 when disabled (compile-time or atomic flag)
- Profiler records must be thread-safe and goroutine-correlated

**Engineering Milestones (DoD):**
- [ ] Overhead measured at 3 op sizes (1K, 1M, 100M elements): p95 overhead < 5% when enabled
- [ ] Chrome-trace export loads in `chrome://tracing` for a 10k-op capture; FLOP counts match analytical model ± 1%

### 1.16 Tensor Serialization [x]
**Engineering Sub-tasks:**
- [ ] Define binary tensor format v1: magic, format-version, dtype code, rank, shape, strides, layout flag, checksum (xxHash64), payload
- [ ] Implement `Save(path)`/`Load(path)` with streaming support for tensors > RAM (mmap/chunked)
- [ ] Implement `MarshalBinary`/`UnmarshalBinary`, JSON (with base64 payload option), and zero-copy mmap load
- [ ] Implement cross-endianness handling and version migration hooks (forward/backward within MAJOR)
- [ ] Implement integrity verification on load and partial-load (subset of dims) API

**Implementation Requirements & Constraints:**
- Serialized payload must be byte-identical for identical tensor content (deterministic, no padding randomness)
- Load path must validate checksum before returning data; corrupted files return `ErrCorruptTensor`

**Engineering Milestones (DoD):**
- [ ] Round-trip fidelity on 100% of dtype×rank matrix (16 dtypes × ranks 0–6); checksum catches 100% of bit-flip injections
- [ ] Save/load throughput ≥ 2 GB/s on NVMe; mmap load reaches first byte < 1 ms

### 1.17 Tensor Compression [x]
**Engineering Sub-tasks:**
- [ ] Implement codec registry: `None`, `LZ4`, `Zstd` (levels 1–19), `FloatQuant` (int8/int4 with scale/zero-point), `SparseRLE`
- [ ] Implement `Compress(tensor, codec)` / `Decompress(buffer, codec)` with codec auto-selection heuristic
- [ ] Implement lossy float compression: quantization + optional error-bound guarantee (max-abs-error param)
- [ ] Implement chunked compression for large tensors (per-chunk headers, random access to chunks)
- [ ] Implement compression ratio/throughput reporting per tensor

**Implementation Requirements & Constraints:**
- Compressed format must be self-describing (codec id in header); decompression validates dtype/shape from header
- Lossy codecs must declare error bounds in header; violations detected on decompress verification

**Engineering Milestones (DoD):**
- [ ] Zstd-3 on float32 noise achieves ≥ 200 MB/s compress / ≥ 800 MB/s decompress; quantized int8 achieves 4:1 ratio within 1% max-abs error on model weights
- [ ] Round-trip lossless for `None/LZ4/Zstd`; lossy error within declared bound on 100% of tested tensors

### 1.18 Tensor Cache [x]
**Engineering Sub-tasks:**
- [ ] Implement LRU tensor cache with capacity (count + bytes) and TTL policies
- [ ] Implement cache key derivation: op-hash of (op-id, input tensor hashes, params)
- [ ] Implement tensor hashing: content hash (fast path: storage hash; slow path: element-wise)
- [ ] Implement cache admission policy (TinyLFU sketch), eviction callbacks, and pin/lock semantics
- [ ] Implement cache metrics: hit/miss/evict counters, hit-rate gauge, per-key size accounting

**Implementation Requirements & Constraints:**
- Cache entries must respect storage aliasing: cached views pin base storage
- Eviction must be O(1) amortized; lock contention must not block readers (RCU/sharded locks)

**Engineering Milestones (DoD):**
- [ ] Hit rate ≥ 90% on repeated-op benchmark (same op, same inputs); eviction overhead < 100 µs per 1000 entries
- [ ] Capacity enforcement exact: cache never exceeds configured byte cap (fault-injection test with 10k entries)

### 1.19 Tensor SIMD [x]
**Engineering Sub-tasks:**
- [ ] Implement SIMD dispatch layer: runtime CPU feature detection (AVX2/AVX-512/Neon/SVE) via CPUID/auxv
- [ ] Implement kernels: `VecAdd`, `VecMul`, `Dot`, `FMA`, `Sum`, `Max`, `Exp`, `Tanh` for 128/256/512-bit lanes
- [ ] Implement tail handling (scalar remainder), alignment prologue, and gather/scatter for non-contiguous strides
- [ ] Implement auto-vectorization guards: `//go:noescape`, asm kernels with Go ABI, fallback scalar paths
- [ ] Implement SIMD benchmark suite with per-feature gating (test skipped if feature absent)

**Implementation Requirements & Constraints:**
- Dispatch must be branch-predictor friendly: feature flags resolved once at init into function pointers
- All SIMD kernels must produce bit-identical results to scalar for integer ops; float ops within 1 ULP

**Engineering Milestones (DoD):**
- [ ] SIMD add/mul ≥ 12× scalar throughput on AVX2 (float32); dot product ≥ 20 GFLOP/s
- [ ] Feature-detection unit test on emulated CPUID tables (100% branch coverage); 0 misaligned-load faults in 1M randomized-alignment runs

---

## PHASE 2 — MEMORY (13 modules)

### 2.1 Arena Allocator [x]
**Engineering Sub-tasks:**
- [ ] Implement bump allocator with size-class pre-sizing and per-thread arenas (thread-local arena registry)
- [ ] Implement `Alloc(size, alignment)` with pointer bump, alignment padding (≤ 64-byte waste cap), and guard-page option
- [ ] Implement `FreeAll` (O(1) reset), scoped sub-arenas with `Reset` semantics, and no individual free
- [ ] Implement arena growth policy: double capacity with `mremap`/realloc fallback, high-water mark tracking
- [ ] Implement arena stats: allocated, committed, wasted, peak, fragmentation estimate

**Implementation Requirements & Constraints:**
- Arena memory must be 64-byte aligned; allocations > 25% of arena capacity go directly to system allocator
- No pointer into an arena may outlive its `Reset` (documented contract; debug mode poisons freed regions)

**Engineering Milestones (DoD):**
- [ ] Alloc throughput ≥ 200M allocs/sec (bump path); allocation latency p99 < 20 ns
- [ ] Fragmentation ≤ 5% on mixed 64B–4KB workload; zero leaks under 1M alloc/reset cycles

### 2.2 Slab Allocator [x]
**Engineering Sub-tasks:**
- [ ] Implement size-class slab allocator: class table (16B → 4KB, geometric/rounded), per-class free lists
- [ ] Implement slab acquisition (page-aligned chunks), object carve, free-list push/pop with LIFO locality
- [ ] Implement per-CPU slab caches to eliminate cross-thread contention
- [ ] Implement class auto-tuning: histogram of request sizes, class table regeneration under lock
- [ ] Implement stats: per-class utilization, slab count, external fragmentation ratio

**Implementation Requirements & Constraints:**
- Free-list operations must be lock-free per-CPU; global slab list lock only on slab exhaustion
- Object headers are forbidden in the hot path (metadata stored in slab header indexing)

**Engineering Milestones (DoD):**
- [ ] Alloc/free pair p99 < 50 ns; per-CPU caches achieve ≥ 10M ops/sec/thread at 16 threads
- [ ] Internal fragmentation ≤ 12.5% worst-case (class rounding bound); utilization report per class

### 2.3 Buddy Allocator [x]
**Engineering Sub-tasks:**
- [ ] Implement power-of-two buddy system: order table (0 → MAX_ORDER), free lists per order
- [ ] Implement `Alloc(order)` with buddy splitting, `Free` with buddy coalescing (XOR buddy-address computation)
- [ ] Implement bitmap-based block tracking for O(1) buddy-state lookup
- [ ] Implement order statistics: per-order free counts, allocation failure diagnostics, watermark
- [ ] Implement integration point: page-granular backing for tensor storage above a size threshold

**Implementation Requirements & Constraints:**
- Buddy allocation is page-granular (4KB minimum); sub-page requests route to slab allocator
- Coalescing must be atomic with respect to concurrent frees of buddies (per-order lock)

**Engineering Milestones (DoD):**
- [ ] Coalescing restores maximal free block in 100% of 10k randomized alloc/free sequences
- [ ] Fragmentation ≤ 25% worst-case (buddy bound); allocation at MAX_ORDER fails cleanly with `ErrOutOfMemory`

### 2.4 Memory Pool [x]
**Engineering Sub-tasks:**
- [ ] Implement generic fixed-size pool: free-list stack, batch refill from backing allocator
- [ ] Implement pool metrics: hit rate, miss rate, wait time, refill count, peak utilization
- [ ] Implement pool autosizing: shrink on sustained low utilization, grow on miss bursts
- [ ] Implement multi-pool coordinator: route requests by size class to dedicated pools
- [ ] Implement pool quarantine: zero-fill on release for sensitive buffers (configurable)

**Implementation Requirements & Constraints:**
- Pool objects must be returned in usable state; release path clears owner references
- Cross-thread returns are lock-free (per-thread return buffers merged on refill)

**Engineering Milestones (DoD):**
- [ ] Pool hit rate ≥ 95% on steady-state workload; miss path latency ≤ 2× direct alloc
- [ ] Zero double-release: double-free detector test (poison pattern) triggers `ErrDoubleFree` 100% of the time

### 2.5 Tensor Pool [x]
**Engineering Sub-tasks:**
- [ ] Implement shape-keyed tensor pool: key = (dtype, shape-hash, device), value = free-list of tensors
- [ ] Implement acquire/release with exact-shape match and nearest-larger fallback (≤ 2× waste cap)
- [ ] Implement pool-aware tensor constructors: `ZerosFromPool`, `EmptyFromPool`
- [ ] Implement reference-counted release: tensors returned only when external refs drop to zero
- [ ] Implement pool pressure governor: hard byte cap, emergency drain, and allocation-deferral queue

**Implementation Requirements & Constraints:**
- Pooled tensors must not retain autograd graph references after release (graph detach on release)
- Pool must be per-device; cross-device acquire routes to the correct device pool

**Engineering Milestones (DoD):**
- [ ] Acquire-from-pool latency ≤ 1 µs p99; allocation traffic to system allocator reduced ≥ 80% on training-loop benchmark
- [ ] Byte cap enforced under adversarial acquire/release storm (10k ops); zero use-after-release (poison test)

### 2.6 Buffer Reuse [x]
**Engineering Sub-tasks:**
- [ ] Implement in-place op analysis: when output shape/dtype match input and no aliasing hazard, write in-place
- [ ] Implement reuse registry: buffer lending with epoch-based invalidation
- [ ] Implement reuse-safe guards: refcount check, alias scan, autograd-leaf protection
- [ ] Implement `WithReusedBuffer` API for explicit reuse in fused pipelines
- [ ] Implement reuse telemetry: bytes saved, reuse rate, rejected-reuse reason histogram

**Implementation Requirements & Constraints:**
- In-place is forbidden when tensor is an autograd leaf, is pooled-pinned, or has > 1 alias
- Epoch invalidation must be globally ordered (monotonic epoch counter)

**Engineering Milestones (DoD):**
- [ ] In-place path verified bit-identical to out-of-place on 200 op cases; zero aliasing violations in 10k adversarial alias graphs
- [ ] Buffer reuse reduces allocation volume ≥ 40% on transformer-layer microbenchmark (bytes-saved metric)

### 2.7 Zero Copy Buffers [x]
**Engineering Sub-tasks:**
- [ ] Implement external-memory import: wrap user pointer/FD/mmap region as tensor storage (no copy)
- [ ] Implement `AsReadOnly` foreign buffer with release-callback registration (user-owned lifetime)
- [ ] Implement zero-copy IPC: shared-memory segment attach (fd passing / named SHM), device-memory import
- [ ] Implement copy-on-write escalation: first write triggers clone with explicit `COW` marker
- [ ] Implement safety contract: lifetime token, `Pin`/`Unpin`, and `Release` handshake

**Implementation Requirements & Constraints:**
- Imported buffers must never be freed by the engine; release callback is mandatory at import time
- Cross-process zero-copy requires identical endianness and page alignment

**Engineering Milestones (DoD):**
- [ ] Import-to-first-op latency < 10 µs; 100% of imported buffers honor release callbacks (callback-count test)
- [ ] COW escalation copies exactly once (write-count test); SHM round-trip throughput ≥ 5 GB/s

### 2.8 Leak Detector [x]
**Engineering Sub-tasks:**
- [ ] Implement allocation stack-trace capture (configurable depth, sampled for hot paths)
- [ ] Implement epoch-based leak scan: snapshot live allocations, diff across checkpoints, report unreleased
- [ ] Implement tensor-level leak detection: storage refcount audit vs. live tensor registry
- [ ] Implement leak report: allocation site, age, size histogram, top-N suspects by bytes
- [ ] Implement test-mode hook: automatic leak assertion at test teardown

**Implementation Requirements & Constraints:**
- Tracker overhead ≤ 3% in production profile mode; full-trace mode is debug-only
- Tracker must itself be leak-free (fixed pre-allocated records, ring overflow policy)

**Engineering Milestones (DoD):**
- [ ] Detects 100% of injected leaks (500-case suite: goroutine-held, closure-captured, pool-missed); false-positive rate < 1%
- [ ] Full-scan of 1M live allocations completes < 2 s; report pinpoints leak site within 3 stack frames

### 2.9 Memory Profiler [x]
**Engineering Sub-tasks:**
- [ ] Implement heap profiler: live bytes, alloc rate, GC/allocator stats, per-site attribution
- [ ] Implement time-series capture: RSS, heap, tensor-pool bytes, arena committed, at 1 Hz
- [ ] Implement `pprof`-compatible heap profiles plus custom tensor-allocation profiles
- [ ] Implement hotspot analysis: top allocation sites by count/bytes with symbolization
- [ ] Implement OOM forensics: pre-failure ring buffer (last 10k allocation events) dumped on failure

**Implementation Requirements & Constraints:**
- Profiler must support both Go runtime metrics and custom engine allocator metrics in one view
- Time-series must be lock-free (per-thread buffers merged on read)

**Engineering Milestones (DoD):**
- [ ] Live-byte accounting matches `runtime.ReadMemStats` within 1%; attribution covers ≥ 98% of allocations
- [ ] OOM forensics dump captures root-cause site in ≥ 90% of induced-OOM tests; overhead < 2% CPU

### 2.10 Fragmentation Report [x]
**Engineering Sub-tasks:**
- [ ] Implement internal fragmentation metric: Σ(class_size − requested) per allocator
- [ ] Implement external fragmentation metric: 1 − (largest_free_block / total_free)
- [ ] Implement per-allocator, per-size-class, per-device fragmentation tables
- [ ] Implement trend capture: fragmentation index over time with alert thresholds
- [ ] Implement compaction advisor: recommends pool-class retuning when index > threshold

**Implementation Requirements & Constraints:**
- Metrics must be computable without stopping the world (sampled snapshots acceptable, error-bounded)
- Fragmentation index must be normalized 0.0–1.0 for cross-run comparability

**Engineering Milestones (DoD):**
- [ ] Metrics match ground-truth post-mortem computation within 5% on synthetic workloads
- [ ] Advisor produces actionable retuning ≥ 80% of the time when index > 0.5 (evaluated on 50 scenarios)

### 2.11 Lifetime Analysis [x]
**Engineering Sub-tasks:**
- [ ] Implement liveness tracking: first-use/last-use op indices per buffer via graph traversal
- [ ] Compute buffer lifetimes as intervals `[first_op, last_op]` over the execution schedule
- [ ] Implement lifetime overlap graph for allocator planning input
- [ ] Implement in-place reuse candidate detection: non-overlapping lifetimes with compatible dtype/shape
- [ ] Integrate lifetime intervals into the memory planner (Phase 0.6/6 planner interface)

**Implementation Requirements & Constraints:**
- Analysis must be conservative for loops: loop-carried buffers extend lifetime to loop exit
- Analysis runs on the lowered graph (post-optimizer), not the source IR

**Engineering Milestones (DoD):**
- [ ] Lifetime intervals validated against manual annotation on 50 graphs (100% match); overlap graph has no false negatives
- [ ] Analysis completes in O(V+E) — verified on 10k-node graph < 100 ms

### 2.12 Escape Analysis [x]
**Engineering Sub-tasks:**
- [ ] Implement stack-allocation eligibility: tensors with no closure capture, no cross-goroutine escape, no address-taken escape
- [ ] Implement escape classification: `NoEscape`, `EscapeToHeap`, `EscapeToInterface`, `EscapeToCaller`
- [ ] Implement flow-sensitive analysis over the call graph (context-insensitive, 1-CFA minimum)
- [ ] Implement escape report per function with actionable hints (e.g., "pass by value instead of pointer")
- [ ] Implement stack-frame sizing integration for eligible tensors (frame budget check)

**Implementation Requirements & Constraints:**
- Analysis is sound (may over-escape, never under-escape); unsound optimizations are forbidden
- Stack-allocated tensors must be zero-initialized identically to heap path

**Engineering Milestones (DoD):**
- [ ] Analysis is sound on 100% of the test corpus (no under-escape); ≥ 20% of short-lived tensors become stack-eligible on benchmark suite
- [ ] Escape report generated for 100% of internal functions; analysis runtime < 1× compile time budget (≤ 500 ms on 1k functions)

### 2.13 Memory Planner [x]
**Engineering Sub-tasks:**
- [ ] Implement plan generation from lifetime intervals: greedy allocation with reuse-first policy
- [ ] Implement plan cost model: peak bytes, allocation count, copy count (for non-in-place reuse)
- [ ] Implement plan variants: `Greedy`, `FirstFit`, `BestFit`, `ArenaScoped` with strategy selection API
- [ ] Implement plan validation: no use-after-free, no overlap without alias, budget compliance
- [ ] Implement plan application: pre-allocate buffers, bind tensor slots, execute with plan, release on scope exit

**Implementation Requirements & Constraints:**
- Planner must guarantee memory-safety under all valid plans (validated before execution)
- Peak-bytes estimate must upper-bound actual peak (never under-promise)

**Engineering Milestones (DoD):**
- [ ] Planned peak memory ≤ 1.1× optimal on 30 benchmark graphs; plan validation rejects 100% of unsafe plans in adversarial suite
- [ ] Plan application reduces allocator calls ≥ 60% on inference-graph benchmark

---

## PHASE 3 — AUTOGRAD (11 modules)

### 3.1 Dynamic Graph [x]
**Engineering Sub-tasks:**
- [ ] Implement tape-backed dynamic graph: node created per op at execution time, edges = data dependencies
- [ ] Implement node payload: op-id, input/output value refs, backward-fn closure, backward-hooks
- [ ] Implement graph growth policy: incremental node allocation from pool, cap on retained graph size
- [ ] Implement dynamic control-flow support: ops inside loops/conditionals recorded with execution-id correlation
- [ ] Implement graph introspection API: `GraphSnapshot()` (immutable view), node count, op histogram

**Implementation Requirements & Constraints:**
- Graph construction must add ≤ 200 ns/op overhead (amortized, pooled nodes)
- Retained-graph memory is bounded by `MaxGraphBytes`; overflow triggers checkpoint-and-truncate with gradient accumulation

**Engineering Milestones (DoD):**
- [ ] Backward pass on dynamic graph matches analytical gradients on 200 random computation graphs (rel. error < 1e-5)
- [ ] Construction overhead ≤ 200 ns/op measured on 1M-op chain; memory cap enforced in stress test

### 3.2 Static Graph [x]
**Engineering Sub-tasks:**
- [ ] Implement declarative graph builder: define ops without execution, then `Compile()` → executable plan
- [ ] Implement shape/type inference at build time with eager error reporting
- [ ] Implement placeholder/parameter binding: feed dictionary, parameter store, bind-time validation
- [ ] Implement static-graph optimization handoff to Phase 5 optimizer pipeline
- [ ] Implement graph freezing: constant-fold parameters, fix execution plan, export `FrozenGraph`

**Implementation Requirements & Constraints:**
- Static graph must reject shape-incompatible connections at build time (no deferred failures)
- Frozen graph must be immutable and thread-safe for concurrent `Run` calls

**Engineering Milestones (DoD):**
- [ ] Static-graph builds fail-fast on 100% of malformed graphs in 1k-case suite; compile+run matches eager mode within 1e-6
- [ ] Frozen graph `Run` latency ≤ dynamic-graph latency for same computation (no per-op dispatch overhead)

### 3.3 Tape Engine [x]
**Engineering Sub-tasks:**
- [ ] Implement operation tape: append-only record of (op, inputs, outputs, backward closure)
- [ ] Implement tape modes: `Train` (record), `Eval` (no record), `NoGrad` (scoped suppression)
- [ ] Implement tape truncation strategies: window, checkpoint (recompute-on-backward), gradient-accumulation merge
- [ ] Implement tape replay for higher-order gradients (nested tape construction)
- [ ] Implement tape diagnostics: record count, bytes, ops/sec, retention policy report

**Implementation Requirements & Constraints:**
- Tape writes must not allocate per-op beyond pooled record; closures reference pre-allocated context structs
- Checkpoint recompute must be deterministic and side-effect-free

**Engineering Milestones (DoD):**
- [ ] Tape memory ≤ 1.5× output-bytes for a 100-layer MLP; truncation reduces retention ≥ 70% with identical gradients (bitwise, same thread count)
- [ ] Eval mode shows 0 tape allocations; nested-tape higher-order gradients match finite differences

### 3.4 Gradient Engine [x]
**Engineering Sub-tasks:**
- [ ] Implement reverse-mode AD: topological order traversal, backward dispatch per op, chain-rule application
- [ ] Implement gradient accumulation buffers with `+=` semantics for fan-out nodes
- [ ] Implement `Gradients(loss, wrt)` API: multi-target, `stop_gradient` markers, disconnected-input policy
- [ ] Implement forward-mode AD for Jacobian-vector products (dual-number carrier)
- [ ] Implement gradient value reuse and zero-init policy for accumulation buffers

**Implementation Requirements & Constraints:**
- Backward pass must process nodes in reverse topological order exactly once per tape
- Accumulation order must be deterministic per schedule for reproducible training

**Engineering Milestones (DoD):**
- [ ] Gradients verified against numerical differentiation (central differences) on 500 random graphs, rel. error < 1e-5
- [ ] Backward throughput ≥ 50% of forward throughput (rule of thumb) on 100-layer MLP; zero gradient leaks between `Gradients` calls

### 3.5 Gradient Hooks [x]
**Engineering Sub-tasks:**
- [ ] Implement pre/post backward hooks: register per-tensor or per-node, ordered execution, mutable gradient payload
- [ ] Implement hook types: transform (map grad), observe (read-only), conditional (predicate-gated)
- [ ] Implement hook removal API and one-shot hooks (auto-deregister after fire)
- [ ] Implement hook execution isolation: panic in hook → wrapped error, not engine crash
- [ ] Implement hook debugging: fire-count, timing, and payload snapshot per hook

**Implementation Requirements & Constraints:**
- Hooks execute in registration order; hooks must not mutate graph structure mid-backward
- Hook overhead must be O(1) per node when no hooks registered (nil-check fast path)

**Engineering Milestones (DoD):**
- [ ] Hook ordering verified on 100-registration chains; panic-in-hook produces typed error with node context
- [ ] Zero-overhead verified: backward with zero hooks ≤ backward baseline + 1%; hook fire-count 100% accurate

### 3.6 Higher Order Gradients [x]
**Engineering Sub-tasks:**
- [ ] Implement double-backward: backward closures themselves must be differentiable (tape-of-tapes)
- [ ] Implement Hessian-vector products via nested reverse mode without materializing Hessian
- [ ] Implement `grad(grad(f))` API with second-order tape management and memory planning
- [ ] Implement Jacobian-vector and vector-Jacobian products with checkpointed recomputation
- [ ] Implement order limits: `MaxGradientOrder` guard with `ErrUnsupportedOrder` beyond bound

**Implementation Requirements & Constraints:**
- Second-order memory must be planned (not naively retained); recompute strategy mandatory for orders ≥ 2
- Higher-order path must fall back to finite differences only in debug-verification mode

**Engineering Milestones (DoD):**
- [ ] Hessian-vector products match finite-difference Hessian on 50 test functions (rel. error < 1e-4)
- [ ] Order-2 memory ≤ 3× first-order memory on MLP benchmark; order-3+ returns typed error cleanly

### 3.7 Graph Pruning [x]
**Engineering Sub-tasks:**
- [ ] Implement gradient-irrelevance analysis: mark nodes with zero gradient path to loss
- [ ] Implement dead-branch pruning: remove nodes whose outputs do not influence any backward edge
- [ ] Implement no-grad subgraph elision: skip recording and execution of `stop_gradient` regions
- [ ] Implement pruning safety validation: pruned graph produces bit-identical gradients
- [ ] Implement prune reporting: nodes removed, bytes saved, per-op breakdown

**Implementation Requirements & Constraints:**
- Pruning must never remove nodes with side effects (stateful ops, RNG, I/O)
- Pruning runs post-tape-construction, pre-backward dispatch

**Engineering Milestones (DoD):**
- [ ] Pruned backward equals unpruned backward bit-for-bit on 200 graphs; side-effect nodes preserved in 100% of cases
- [ ] Pruning removes ≥ 30% of nodes on graphs with 20% dead branches (synthetic suite); validation runtime < 10% of backward

### 3.8 Gradient Fusion [x]
**Engineering Sub-tasks:**
- [ ] Implement gradient-op pattern matching: consecutive elementwise grads, grad-of-broadcast, grad-of-reduce chains
- [ ] Implement fusion codegen: single-kernel fused backward for matched patterns
- [ ] Implement fusion legality checks: no fusion across stateful ops, memory-alias hazards, or non-associative float orders
- [ ] Implement fused-kernel cache: hash pattern → compiled kernel, LRU-evicted
- [ ] Implement fusion telemetry: patterns matched, kernels saved, speedup distribution

**Implementation Requirements & Constraints:**
- Fused gradients must preserve accumulation order semantics (documented tolerance) or be gated by deterministic flag
- Fusion only when pattern covers ≥ 3 ops to amortize dispatch

**Engineering Milestones (DoD):**
- [ ] Fused backward matches unfused within documented tolerance on 100 pattern instances; ≥ 15% backward speedup on fused regions
- [ ] Fusion engine processes 10k-node graph in < 50 ms; zero incorrect fusions in adversarial pattern suite

### 3.9 Graph Cleanup [x]
**Engineering Sub-tasks:**
- [ ] Implement post-backward cleanup: release backward closures, drop tape nodes, recycle node pool entries
- [ ] Implement stale-reference sweep: detect and break tensor→node→tensor cycles (cycle-collector pass)
- [ ] Implement cleanup triggers: scope exit, tape truncation, memory pressure, explicit `Cleanup()`
- [ ] Implement idempotent cleanup: repeated calls are no-ops; concurrent cleanup is safe (epoch-guarded)
- [ ] Implement cleanup metrics: nodes freed, bytes reclaimed, cycles broken, sweep duration

**Implementation Requirements & Constraints:**
- Cleanup must never free tensors still referenced by live gradients or user handles (refcount gate)
- Cleanup latency must be bounded: incremental sweeps, no unbounded single-pass pauses > 10 ms

**Engineering Milestones (DoD):**
- [ ] Post-cleanup memory returns to within 5% of pre-graph baseline on 100 iteration training loop
- [ ] Zero premature frees in refcount stress test; incremental sweeps keep p99 pause < 10 ms

### 3.10 Graph Visualizer [x]
**Engineering Sub-tasks:**
- [ ] Implement graph → DOT exporter: nodes colored by op-class (forward/backward/gradient), edges labeled with shapes
- [ ] Implement GraphViz layout hints: rank constraints for topological ordering, clusters by subgraph
- [ ] Implement interactive HTML export: D3 force-directed graph with zoom, node-detail tooltips, gradient-flow animation
- [ ] Implement graph summaries: critical path highlight, hot-node heatmap (by time), memory-footprint overlay
- [ ] Implement export filters: op-type filter, depth limit, gradient-only view, threshold-based pruning for display

**Implementation Requirements & Constraints:**
- Exporter must handle 100k-node graphs without OOM (streaming export, pagination)
- Visualizer output is deterministic for a given graph (stable node ids)

**Engineering Milestones (DoD):**
- [ ] DOT export of 10k-node graph renders in GraphViz < 5 s; HTML export of 1k nodes interactive at 60 fps
- [ ] Visualized gradient flow matches tape traversal order in 100% of sampled subgraphs

### 3.11 Debug Mode [x]
**Engineering Sub-tasks:**
- [ ] Implement debug mode flags: `CheckNumerics` (NaN/Inf per op), `SlowChecks` (shape/alias invariants), `DumpGraph` (per-op snapshots)
- [ ] Implement gradient checker: automatic finite-difference comparison per trainable tensor at user-selected steps
- [ ] Implement op-trace debugger: step through ops, inspect inputs/outputs, break-on-condition (NaN, value threshold)
- [ ] Implement debug replay: deterministic seed capture → exact graph replay with diff-at-step analysis
- [ ] Implement debug overhead governor: auto-disable beyond configurable latency budget

**Implementation Requirements & Constraints:**
- Debug mode is opt-in at session start; never enabled implicitly in production paths
- All debug state must be isolated (no pollution of production tensors or graphs)

**Engineering Milestones (DoD):**
- [ ] Gradient checker flags injected-gradient bugs in 100% of 20 seeded bug cases; NaN detection catches within 1 op of injection
- [ ] Debug-mode overhead is bounded and reported (e.g., ≤ 10× latency, measured); replay diff detects single-bit perturbations

---

## PHASE 4 — ASTROIR (14 modules)

### 4.1 AST [x]
**Engineering Sub-tasks:**
- [ ] Define AST node taxonomy: `Literal`, `Identifier`, `BinaryOp`, `UnaryOp`, `Call`, `TensorDecl`, `Function`, `If`, `For`, `While`, `Assign`, `Return`, `Index`, `Slice`, `BroadcastExpr`
- [ ] Implement AST with parent links, source spans (line/col, byte offsets), and trivia (comments) attachment
- [ ] Implement AST deep-clone (immutable-by-default) and structural `Equal`
- [ ] Implement visitor pattern (`Walk`, `WalkMut`) with pre/post order and child-list mutation
- [ ] Implement AST pretty-printer (round-trip stable) and source-map generation for error reporting

**Implementation Requirements & Constraints:**
- AST nodes must carry span information on every node; no span-less nodes permitted
- Visitor must be total: every node type has a case (exhaustive switch enforced by tests)

**Engineering Milestones (DoD):**
- [ ] AST round-trips through printer → reparse with zero structural diffs on 200 programs
- [ ] Visitor coverage test enumerates 100% of node types; clone-equality holds on 1k random ASTs

### 4.2 HIR (High-Level IR) [x]
**Engineering Sub-tasks:**
- [ ] Define HIR: op-level graph with named values, control-flow as structured blocks, region-based scoping
- [ ] Implement AST → HIR lowering: desugaring (e.g., `for-each` → index loop), name resolution to SSA-like values
- [ ] Implement HIR type environment: scoped symbol table, shadowing rules, type annotations
- [ ] Implement HIR verification: dominance, single-assignment-per-scope, region well-formedness
- [ ] Implement HIR dumping (text + JSON) with span back-mapping to source

**Implementation Requirements & Constraints:**
- HIR is typed and region-scoped; all identifiers resolved before HIR emission
- HIR must preserve source spans for all diagnostics through later IR stages

**Engineering Milestones (DoD):**
- [ ] HIR verifier rejects 100% of malformed HIR in mutation-fuzz suite; lowering correct on 300-program corpus
- [ ] Every HIR value has span + type; diagnostic location accuracy = 100% (within 1 line)

### 4.3 MIR (Mid-Level IR) [x]
**Engineering Sub-tasks:**
- [ ] Define MIR: linear instruction list per block, explicit temporaries, memory ops (alloc/load/store), call ops
- [ ] Implement HIR → MIR lowering: expression trees → instruction sequences with SSA temporaries
- [ ] Implement MIR operand model: registers (SSA) + stack slots + memory references
- [ ] Implement MIR liveness analysis and slot allocation prep (pre-regalloc)
- [ ] Implement MIR canonical form: normalized operand order, constant canonicalization, nop removal

**Implementation Requirements & Constraints:**
- MIR must be target-independent; backend-specific ops only appear post-lowering
- Every MIR instruction has ≤ 2 source operands and 1 destination (machine-like)

**Engineering Milestones (DoD):**
- [ ] MIR instruction count ≤ 3× HIR op count on corpus (no blowup); canonicalization is idempotent
- [ ] Liveness analysis (live-range sets) verified against brute-force on 100 functions

### 4.4 SSA IR [x]
**Engineering Sub-tasks:**
- [ ] Implement SSA construction: `Function`, `Block`, `PhiNode`, dominance-frontier-based placement
- [ ] Implement SSA renaming via worklist algorithm over dominance tree
- [ ] Implement SSA verification: def-dominates-use, single definition, phi correctness at block entries
- [ ] Implement SSA destruction (phi elimination → move insertion) for backend handoff
- [ ] Implement SSA utilities: `ReplaceAllUsesWith`, `InstructionBuilder`, `ValueHandle` (updates on RAUW)

**Implementation Requirements & Constraints:**
- Phi nodes only at block starts; critical edges must be split before phi insertion
- SSA form must be maintained through all mid-end passes (verifier runs after each pass)

**Engineering Milestones (DoD):**
- [ ] SSA construction correct on all 500 control-flow graphs in test corpus (def-dominates-use 100%)
- [ ] RAUW propagates through phi chains correctly in 10k-op mutation test; verifier runs in < 5 ms on 10k-instruction function

### 4.5 Graph IR [x]
**Engineering Sub-tasks:**
- [ ] Define dataflow graph IR: typed nodes (op + attributes), directed edges (tensor dependencies), ordered outputs
- [ ] Implement graph mutation API: `AddNode`, `RemoveNode`, `ReplaceNode`, `Rewire` with topological-order maintenance
- [ ] Implement graph properties: `IsAcyclic`, `Inputs`, `Outputs`, `Consumers(node)`, `Dependencies(node)`
- [ ] Implement subgraph extraction (region cut) and inlining (collapse function call into caller graph)
- [ ] Implement Graph IR ↔ SSA IR bidirectional conversion with equivalence checking

**Implementation Requirements & Constraints:**
- Graph IR enforces single-writer per tensor value; multi-consumer requires explicit fork semantics
- Conversion to SSA inserts phis at merge points; conversion back must preserve semantics

**Engineering Milestones (DoD):**
- [ ] Graph mutation invariants hold after 100k random mutations (acyclicity, single-writer); topological sort always valid
- [ ] SSA↔Graph round-trip is semantics-preserving on 200 functions (equivalence checker, bit-identical outputs)

### 4.6 CFG (Control Flow Graph) [x]
**Engineering Sub-tasks:**
- [ ] Implement CFG construction from blocks: basic-block identification, terminator-based edge insertion
- [ ] Implement CFG analysis: entry/exit identification, reachability (from entry), infinite-loop detection
- [ ] Implement CFG transformations: block merging, dead-block removal, edge splitting (critical edges)
- [ ] Implement CFG serialization (DOT + JSON) with loop/region coloring
- [ ] Implement CFG validation: every edge connects valid terminators, exactly one entry, all exits reachable

**Implementation Requirements & Constraints:**
- CFG nodes correspond 1:1 to basic blocks; no empty blocks post-canonicalization
- All loop structures must have single-entry (structured) form after transformation passes

**Engineering Milestones (DoD):**
- [ ] CFG edge count = terminator-target count on 100% of functions; reachability marks 100% of reachable blocks
- [ ] Dead-block removal eliminates all unreachable blocks without altering semantics (100-function equivalence test)

### 4.7 DFG (Data Flow Graph) [x]
**Engineering Sub-tasks:**
- [ ] Implement DFG extraction from SSA: value-def → use edges, constant edges, control-dependency edges
- [ ] Implement DFG analyses: reaching definitions, live values, use-def chains, def-use chains
- [ ] Implement DFG scheduling: list scheduling with resource model (op latency, port pressure)
- [ ] Implement DFG cycle detection (feedback arcs) and cut-point analysis for pipelining
- [ ] Implement DFG visualization: layered (Sugiyama) layout export

**Implementation Requirements & Constraints:**
- DFG must distinguish true data deps from anti/output deps (post-SSA, primarily true deps)
- Scheduling model requires per-op latency table from backend registry

**Engineering Milestones (DoD):**
- [ ] Reaching-definitions and liveness match brute-force on 100 functions; def-use chains cover 100% of uses
- [ ] Scheduled DFG respects resource constraints (zero over-commit in assertion build) on 50 benchmark graphs

### 4.8 Dominator Tree [x]
**Engineering Sub-tasks:**
- [ ] Implement dominator computation: iterative Cooper-Harvey-Kennedy algorithm over reverse post-order
- [ ] Implement `IDom`, `DomTree`, `Dominates(a, b)`, `CommonDominator`
- [ ] Implement dominance frontiers and dominance boundary computation for phi placement
- [ ] Implement loop detection via back-edges (dominator-based): natural loops, nesting depth, loop hierarchy
- [ ] Implement domtree incremental maintenance API for graph edits (recompute-region optimization)

**Implementation Requirements & Constraints:**
- Algorithm must run in O(V·E) worst-case with practical near-linear performance; RPO numbering mandatory
- Loop detection must identify all natural loops; irreducible loops flagged with diagnostic

**Engineering Milestones (DoD):**
- [ ] Dominators match reference implementation on 500 CFGs (100% node match); `Dominates` answers 1M queries < 100 ms
- [ ] Loop identification correct (headers, bodies) on 200 loop-laden functions; irreducible CF detected and reported

### 4.9 Dependency Graph [x]
**Engineering Sub-tasks:**
- [ ] Implement dependency graph: nodes = ops/values, edges = data + control + memory deps
- [ ] Implement memory-dependence analysis: alias-based ordering, may/must dependence classification
- [ ] Implement dependency-cycle detection with SCC computation (Tarjan) and cycle-report extraction
- [ ] Implement parallelism extraction: antichains / independent sets from dependency graph
- [ ] Implement dependency visualization and critical-path computation (longest path)

**Implementation Requirements & Constraints:**
- Memory deps must be conservative (may-dependence default); may-not-miss real hazards
- Critical-path computation assumes per-op latency table; zero-latency edges (constants) excluded

**Engineering Milestones (DoD):**
- [ ] SCC computation identifies 100% of cycles in cyclic-graph suite; independent sets are provably conflict-free (schedule-and-check test)
- [ ] Critical path within 1% of simulation on 50 graphs; parallelism extraction achieves ≥ 80% theoretical ILP

### 4.10 Shape Inference [x]
**Engineering Sub-tasks:**
- [ ] Implement shape inference rules per op: elementwise (broadcast), reduce (dim drop), matmul (contracting dims), conv (kernel/stride/padding formula)
- [ ] Implement symbolic shape support: unknown dims as symbols with constraint propagation (dim equality, divisibility)
- [ ] Implement inference engine: worklist propagation over graph with join at merge points
- [ ] Implement shape validation failure diagnostics: expected vs. actual with op context
- [ ] Implement inference caching: shape results memoized per node, invalidated on graph edit

**Implementation Requirements & Constraints:**
- Inference must terminate on all valid graphs (monotone constraint lattice, no unbounded symbol growth)
- Unknown dims must propagate soundly: never infer a wrong concrete shape

**Engineering Milestones (DoD):**
- [ ] Shape inference matches NumPy semantics on 1000 op graphs; symbolic cases solved in 100% of linear-constraint instances
- [ ] Failure diagnostics name the offending op + dims in ≥ 95% of malformed-graph cases; inference < 50 ms on 10k-node graph

### 4.11 Type Inference [x]
**Engineering Sub-tasks:**
- [ ] Implement dtype inference: per-op type rules, promotion lattice, integer-typing defaults
- [ ] Implement type unification for polymorphic ops (e.g., `where`, `concat`) with constraint solving
- [ ] Implement type-environment propagation through control flow (join = meet of environments)
- [ ] Implement mixed-precision inference: policy-driven dtype selection (fp16/bf16/fp32) with fallback rules
- [ ] Implement type diagnostics: expected vs. inferred, coercion sites, precision-loss warnings

**Implementation Requirements & Constraints:**
- Type inference must be sound: inferred dtype always satisfies op requirements
- Promotion never silently downcasts below user-specified policy floor

**Engineering Milestones (DoD):**
- [ ] Inference agrees with reference type-checker on 500 typed programs; promotion rules match NumPy lattice on 200 dtype combinations
- [ ] Zero unsound inferences in adversarial corpus; mixed-precision policy honored in 100% of policy-violation test cases

### 4.12 Graph Validation [x]
**Engineering Sub-tasks:**
- [ ] Implement structural validation: acyclicity (for feedforward), single-writer, well-formed attributes, port arity
- [ ] Implement semantic validation: dtype/shape compatibility at every edge, device consistency, memory-budget feasibility
- [ ] Implement attribute validation: enum ranges, tensor-attribute shapes, required-attribute presence
- [ ] Implement validation report: ordered error list with severity, node refs, and remediation hints
- [ ] Implement `ValidateGraph` public API with mode flags (fast/deep) and incremental validation on edit

**Implementation Requirements & Constraints:**
- Fast validation must be O(V+E); deep validation may run shape/type inference (bounded)
- Validation must never mutate the graph; all errors reported before any failure abort

**Engineering Milestones (DoD):**
- [ ] Validator catches 100% of injected errors across 20 error categories; zero false positives on 500 valid graphs
- [ ] Fast validation < 5 ms and deep < 100 ms on 10k-node graph; report contains ≥ 90% actionable remediation hints

### 4.13 Graph Serialization [x]
**Engineering Sub-tasks:**
- [ ] Define Graph IR serialization format v1: header (format version, IR version), node table, edge table, attribute blobs, metadata, checksum
- [ ] Implement `MarshalBinary`/`UnmarshalBinary` with schema evolution (optional fields, unknown-field skip)
- [ ] Implement forward/backward compatibility: version negotiation, migration registry (vN→vN+1 transforms)
- [ ] Implement compact encoding: interned string table, delta-encoded indices, zstd container option
- [ ] Implement integrity: per-node and whole-graph checksums, canonical byte output (deterministic serialization)

**Implementation Requirements & Constraints:**
- Serialized form must be deterministic (same graph → same bytes) for content addressing
- Deserialization must be total: malformed input returns typed errors, never panics

**Engineering Milestones (DoD):**
- [ ] Round-trip on 100% of graphs in corpus (10k graphs); checksum detects 100% of corruption injections
- [ ] Migration chain v1→v3 applied correctly on legacy fixtures; unknown-field skip preserves 100% of known data

### 4.14 Graph Visualization [x]
**Engineering Sub-tasks:**
- [ ] Implement Graph IR → DOT exporter: op glyphs, dtype/shape labels, color by op class, cluster by scope
- [ ] Implement layered layout export (Sugiyama-compatible) for acyclic graphs with cycle-breaking
- [ ] Implement interactive viewer data: JSON graph (nodes/edges with attributes) for web viewer, pagination for large graphs
- [ ] Implement visualization overlays: profiling heat (per-node time/memory), gradient flow direction, data-dependence highlighting
- [ ] Implement export filters: depth limits, op-type filters, threshold pruning, subgraph focus

**Implementation Requirements & Constraints:**
- Export must stream for graphs > 50k nodes (bounded memory, chunked output)
- Node ids in visualization must be stable and match textual dump ids

**Engineering Milestones (DoD):**
- [ ] DOT export of 10k-node graph < 2 s and renders in GraphViz; web viewer interactive (≥ 30 fps) at 5k nodes
- [ ] Overlay data matches profiler output within 1%; filters produce connected subgraphs in 100% of tests

---

## PHASE 5 — OPTIMIZER (11 modules)

### 5.1 Constant Folding [x]
**Engineering Sub-tasks:**
- [ ] Implement constant-value lattice: `Const`, `NonConst`, `Unknown` with join semantics
- [ ] Implement fold rules for all pure ops: arithmetic (incl. identities: `x+0`, `x*1`, `x*0`), shape ops, casts
- [ ] Implement multi-pass folding with fixpoint iteration (fold → simplify → re-fold)
- [ ] Implement fold for tensor attributes: fold constant subgraphs into single constant tensor
- [ ] Implement fold safety: no folding of ops with side effects, NaN semantics preservation, overflow checks for int

**Implementation Requirements & Constraints:**
- Folding must preserve IEEE-754 semantics exactly (no reassociation of float expressions)
- Folded constants must be deduplicated (constant interning) to avoid graph bloat

**Engineering Milestones (DoD):**
- [ ] Folding matches evaluated results bit-for-bit on 1000 constant subgraphs; identities applied in 100% of applicable cases
- [ ] Fixpoint converges in ≤ 4 passes on all test graphs; zero semantic drift on equivalence test suite

### 5.2 Constant Propagation [x]
**Engineering Sub-tasks:**
- [ ] Implement sparse conditional constant propagation (SCCP): lattice values over SSA, worklist propagation
- [ ] Implement conditional constant propagation through control flow: branch resolution, dead-edge pruning
- [ ] Implement propagation into op attributes (e.g., static slice bounds, reduce axes)
- [ ] Implement propagation-then-simplify pipeline: constants exposed → fold → dead-branch removal
- [ ] Implement propagation diagnostics: constants found, branches resolved, blocks removed

**Implementation Requirements & Constraints:**
- SCCP must be monotone over the lattice; iteration terminates at fixpoint
- Branch resolution must conservatively keep both edges when condition is `NonConst`

**Engineering Milestones (DoD):**
- [ ] SCCP finds 100% of constants in synthetic partially-static programs; dead-edge pruning matches unreachable analysis
- [ ] Propagation completes in O(V+E) per pass; equivalence preserved on 300-program corpus

### 5.3 Dead Code Elimination [x]
**Engineering Sub-tasks:**
- [ ] Implement liveness-based DCE: mark reachable outputs, sweep unreachable nodes (post-order mark-and-sweep)
- [ ] Implement aggressive DCE (ADCE): fixpoint of "needed" analysis including side-effect roots
- [ ] Implement side-effect roots: I/O, RNG, stateful ops, external calls — always live
- [ ] Implement DCE for control flow: dead blocks, unreachable branches, empty-block removal
- [ ] Implement DCE safety validation: removed set contains no node with observable effect

**Implementation Requirements & Constraints:**
- DCE must preserve all side-effecting ops; observability defined by the op-side-effect table
- DCE runs iteratively with other passes until fixpoint (bounded, e.g., 10 iterations)

**Engineering Milestones (DoD):**
- [ ] DCE removes 100% of truly dead nodes and 0 side-effecting nodes in 500-case adversarial suite
- [ ] Output equivalence (bit-identical) maintained on 100% of benchmark graphs; fixpoint converges ≤ 10 iterations

### 5.4 Common Subexpression Elimination [x]
**Engineering Sub-tasks:**
- [ ] Implement value-numbering (global, SSA-based): hash-consing per op with operand value numbers
- [ ] Implement GVN with congruence closure for expressions with commutative/associative normalization
- [ ] Implement partial redundancy elimination (PRE): insert computations on partially-redundant paths
- [ ] Implement CSE for tensor ops: shape/dtype/attribute-aware keys (not just syntactic match)
- [ ] Implement redundancy report: expressions eliminated, nodes merged, savings estimate

**Implementation Requirements & Constraints:**
- Value numbering must account for float non-associativity: only reassociate under explicit fast-math flag
- Hash keys must include op, attributes, and operand value numbers — never raw pointers alone

**Engineering Milestones (DoD):**
- [ ] GVN eliminates 100% of redundant computations in redundancy-injection suite; PRE reduces redundant ops ≥ 60% on partial-redundancy benchmarks
- [ ] Zero miscompiles: equivalence checker passes on 300 graphs; CSE lookup p99 < 1 µs

### 5.5 Peephole Optimization [x]
**Engineering Sub-tasks:**
- [ ] Implement pattern-rule engine: match → predicate → rewrite with cost guard
- [ ] Implement rule library (≥ 50 rules): algebraic identities, op-specific simplifications (transpose-of-transpose, reshape-of-reshape, slice-of-slice), strength reduction (pow→mul, mul→shift)
- [ ] Implement rule chaining with fixpoint (bounded iterations) and rule-firing statistics
- [ ] Implement rule soundness: each rule carries a proof obligation (equivalence conditions) validated in tests
- [ ] Implement rule toggles: per-rule enable/disable, cost model gating (apply only when beneficial)

**Implementation Requirements & Constraints:**
- Every rule must be semantics-preserving under the documented conditions; conditional rules check predicates at match time
- Rule engine must not change float evaluation order unless fast-math enabled

**Engineering Milestones (DoD):**
- [ ] All ≥ 50 rules have equivalence tests (property-based, 100 cases each); rule engine converges in ≤ 6 iterations
- [ ] Peephole pass reduces op count ≥ 10% on standard benchmark graphs with zero semantic drift

### 5.6 Operator Fusion [x]
**Engineering Sub-tasks:**
- [ ] Implement fusion pattern detection: elementwise chains (horizontal), broadcast-merge, reduce-then-elementwise (vertical)
- [ ] Implement fusion decision model: arith-intensity gain vs. register-pressure cost, memory-traffic estimator
- [ ] Implement fused-op construction: new op node with fused semantics, input/output port remapping, attribute merge
- [ ] Implement multi-output fusion (fused ops with several consumers) and producer-consumer chain fusion
- [ ] Implement fusion validation: fused graph equivalent to original (shape/dtype/value checks)

**Implementation Requirements & Constraints:**
- Fusion must preserve float semantics for default mode; reassociation only under fast-math
- Fused op must fit backend kernel constraints (max inputs, alignment) — validated pre-emit

**Engineering Milestones (DoD):**
- [ ] Fusion reduces kernel launches ≥ 30% on transformer-layer graphs; memory traffic model predicts within 10% of measurement
- [ ] Fused-graph equivalence 100% on 500 graphs; fusion pass < 100 ms on 10k-node graph

### 5.7 Kernel Fusion [x]
**Engineering Sub-tasks:**
- [ ] Implement kernel-level fusion: map fused op clusters to single GPU/CPU kernel launch plans
- [ ] Implement fusion codegen: generate kernel source (elementwise fused loops) or select precompiled fused kernel
- [ ] Implement register-tiling analysis: working-set estimate per fused kernel, spill avoidance checks
- [ ] Implement fusion boundary handling: load/store insertion at cluster edges, intermediate register promotion
- [ ] Implement kernel-fusion cache: cluster-hash → compiled kernel with LRU and recompilation stats

**Implementation Requirements & Constraints:**
- Fused kernel working set must fit target register file / L1 (else split cluster)
- Generated kernels must be deterministic and bit-exact vs. unfused for integer ops

**Engineering Milestones (DoD):**
- [ ] Fused kernels execute ≥ 1.5× faster than unfused sequence on ≥ 70% of clusters; zero register spills on fitted clusters
- [ ] Codegen output compiles on first attempt ≥ 98% of the time; cache hit rate ≥ 80% on repeated graphs

### 5.8 Loop Fusion [x]
**Engineering Sub-tasks:**
- [ ] Implement loop-fusion analysis: loop nests with identical iteration spaces and compatible bodies
- [ ] Implement fusion legality: no data dependence violation (dependence vector analysis), no ordering hazards
- [ ] Implement fused loop generation: merged body with sequential statement order preserved
- [ ] Implement interchange-fusion combo: fuse then reorder for locality (dependence-safe reordering only)
- [ ] Implement fusion profitability model: fusion vs. kernel-launch overhead, cache-reuse estimate

**Implementation Requirements & Constraints:**
- Fusion requires exact iteration-space equality (or provable equivalence after normalization)
- Statement order within fused body must preserve original execution semantics for dependent stores

**Engineering Milestones (DoD):**
- [ ] Legal fusions applied in 100% of fusable cases; zero illegal fusions in dependence-hazard suite (100 cases)
- [ ] Fused loops achieve ≥ 1.2× speedup on memory-bound pairs; legality checker O(V+E) per loop pair

### 5.9 Loop Unrolling [x]
**Engineering Sub-tasks:**
- [ ] Implement unrolling heuristics: full unroll (trip count ≤ threshold), partial unroll (factor), runtime unroll (trip-unknown)
- [ ] Implement unroll codegen: body replication, epilogue handling for remainder trips, induction-variable substitution
- [ ] Implement unroll cost model: code-size budget, register pressure, I-cache impact, trip-count profiling input
- [ ] Implement unroll + Jam (loop fusion after unroll) for nested loops with safety analysis
- [ ] Implement unroll validation: trip-count semantics identical including remainder paths

**Implementation Requirements & Constraints:**
- Unrolling must handle non-divisible trip counts with correct epilogue; no dropped iterations
- Code-size growth capped (e.g., ≤ 4× body size) to avoid I-cache thrash

**Engineering Milestones (DoD):**
- [ ] Unrolled loops produce identical results on 100% of trip-count sweep (1–1000); epilogue correctness verified on prime trip counts
- [ ] Unrolling yields ≥ 1.3× speedup on vectorizable loops; code-size budget respected in 100% of cases

### 5.10 Graph Simplification [x]
**Engineering Sub-tasks:**
- [ ] Implement graph-level rewrites: identity removal, no-op elision (reshape-to-same-shape, transpose-to-identity), constant subgraph collapse
- [ ] Implement structural simplification: chain flattening (reshape∘reshape → single reshape), branch-to-select conversion
- [ ] Implement attribute simplification: static evaluation of shape/stride attributes, range-based narrowing
- [ ] Implement simplification pipeline orchestration: pass ordering, budget (time/node caps), fixpoint with iteration limit
- [ ] Implement before/after graph diff report: nodes removed/merged/rewritten with reasons

**Implementation Requirements & Constraints:**
- Simplification pipeline is deterministic: same input graph + config → same output graph
- Every rewrite must preserve observable behavior including op ordering of side effects

**Engineering Milestones (DoD):**
- [ ] Simplification reduces node count ≥ 15% on standard graphs; pipeline terminates within budget on 100% of 10k-node graphs
- [ ] Equivalence checker passes 100%; diff report accounts for 100% of node-count delta

### 5.11 Rewrite Engine [x]
**Engineering Sub-tasks:**
- [ ] Implement generic rewrite engine: pattern IR (graph patterns with wildcards), matching algorithm (subgraph isomorphism, backtracking with pruning)
- [ ] Implement rewrite rule DSL: pattern → replacement with fresh-var generation and guard predicates
- [ ] Implement rule engine execution strategies: bottom-up, top-down, exhaust-rule-per-node, worklist-driven
- [ ] Implement cost-based rule selection: rule benefit estimate, conflicting-rule priority, application budget
- [ ] Implement rule provenance: audit trail of applied rules (rule id, location, before/after snapshot)

**Implementation Requirements & Constraints:**
- Matcher must handle commutative edges and variable-arity ops; exponential blowup guarded by node budget
- Engine must be reentrant: rules may schedule additional passes via a controlled API

**Engineering Milestones (DoD):**
- [ ] Pattern matcher finds 100% of injected pattern instances (10k cases) with ≤ 2% false positives; matches in < 1 ms per 1k-node graph
- [ ] Rule engine terminates on all test programs (no infinite rewrite cycles — cycle detection on rule application graphs)

---

## PHASE 6 — COMPILER (10 modules)

### 6.1 Lexer [x]
**Engineering Sub-tasks:**
- [ ] Implement tokenizer: keyword table, operator/follow-set table, identifier/number/string literal scanners
- [ ] Implement number parsing: decimal, hex, float with exponent, underscores, type suffixes (f32, i64)
- [ ] Implement string/char literals with escape processing (\n, \u{XXXX}, raw strings)
- [ ] Implement comment handling (line/block/nested) with trivia preservation for source maps
- [ ] Implement error recovery: illegal-character, unterminated-literal, bad-escape with position tracking and panic-mode recovery

**Implementation Requirements & Constraints:**
- Lexer must be single-pass, O(n), allocation-free for token stream (preallocated slice)
- Max token size bounded (e.g., 1 MB literal cap) to prevent memory exhaustion

**Engineering Milestones (DoD):**
- [ ] Tokenizer throughput ≥ 50 MB/s; error recovery produces valid token stream for 100% of malformed-input corpus
- [ ] Position info accurate (line/col/offset) on 100% of tokens; zero allocation per token in steady state

### 6.2 Parser [x]
**Engineering Sub-tasks:**
- [ ] Implement Pratt/precedence-climbing expression parser with full operator precedence table
- [ ] Implement statement/block parsing: declarations, assignments, control flow, function bodies, tensor literals
- [ ] Implement recovery: panic-mode with sync sets (semicolon, brace, keyword), error node insertion
- [ ] Implement AST construction with span attachment and ambiguity resolution (dangling-else, unary-minus)
- [ ] Implement parse diagnostics: expected-token sets, contextual suggestions, error-count cap (fail-fast)

**Implementation Requirements & Constraints:**
- Parser must be LL(k)-bounded (k ≤ 2 lookahead); no exponential backtracking
- Error recovery must not lose more than one statement per error

**Engineering Milestones (DoD):**
- [ ] Parser accepts 100% of valid grammar corpus (500 programs); rejects 100% of invalid corpus with ≤ 5 errors per program reported
- [ ] Parse rate ≥ 10k LOC/s; AST spans correct on 100% of sampled nodes

### 6.3 Semantic Analysis [x]
**Engineering Sub-tasks:**
- [ ] Implement name resolution: scoped symbol tables, declaration-before-use, shadowing policy, import resolution
- [ ] Implement type checking: op/dtype compatibility, arity checks, return-type conformance, control-flow typing
- [ ] Implement borrow/alias checking: mutable-ref uniqueness for in-place ops, lifetime constraints
- [ ] Implement const-evaluability marking and compile-time assertion evaluation
- [ ] Implement diagnostics pipeline: error codes, multi-error reporting (cap + severity sort), fix suggestions

**Implementation Requirements & Constraints:**
- Name resolution must be single-pass over HIR with post-hoc fixups for forward references (functions)
- All diagnostics carry span + code + severity; analyzer never mutates AST semantics

**Engineering Milestones (DoD):**
- [ ] Resolver handles 100% of scoping cases (100 nested scopes test); type checker catches 100% of seeded type errors (200 cases)
- [ ] Analysis completes in O(program size) — 100k-LOC program < 5 s; zero false errors on valid corpus

### 6.4 Graph Builder [x]
**Engineering Sub-tasks:**
- [ ] Implement HIR/MIR → Graph IR lowering: expression trees → dataflow nodes, statements → sequenced ops
- [ ] Implement tensor op construction: attribute extraction, port assignment, intermediate value naming
- [ ] Implement function-call lowering: inline (small functions) vs. call-node (large) decision with threshold
- [ ] Implement control-flow lowering: structured branches/loops → graph regions with merge nodes
- [ ] Implement builder diagnostics: unsupported constructs, lowering-failure recovery, fallback to interpretable subgraph

**Implementation Requirements & Constraints:**
- Lowered graph must be in Graph IR normal form: no empty nodes, canonical port order
- Builder must preserve source spans end-to-end for diagnostics

**Engineering Milestones (DoD):**
- [ ] Lowered graph passes `ValidateGraph` on 100% of valid programs; op count within 2× source op count
- [ ] Inline/call decision threshold tuned: inlining reduces call overhead ≥ 20% on microbenchmark suite

### 6.5 Graph Lowering [x]
**Engineering Sub-tasks:**
- [ ] Implement high-op → low-op decomposition: e.g., `matmul` → `gemm` + layout ops, `conv` → im2col + gemm (strategy-selectable)
- [ ] Implement device-specific lowering: CPU (vector loops), future GPU (thread-mapping annotations)
- [ ] Implement memory-op insertion: alloca/load/store per lifetime analysis (Phase 2.11 integration)
- [ ] Implement legalization: replace unsupported ops with supported equivalents until target op-set satisfied
- [ ] Implement lowering verification: pre/post equivalence (shape/dtype/value) on sampled runs

**Implementation Requirements & Constraints:**
- Lowering is target-driven: op-set legality table per backend; unknown ops fail with `ErrUnsupportedOp`
- Legalization must terminate (op-complexity measure decreases per rewrite)

**Engineering Milestones (DoD):**
- [ ] Lowered graph contains only backend-legal ops in 100% of cases; equivalence holds on 300-program suite
- [ ] Decomposition respects memory budget: inserted allocs within planner bounds; lowering < 200 ms on 10k-node graphs

### 6.6 Kernel Selection [x]
**Engineering Sub-tasks:**
- [ ] Implement kernel registry query: by op, dtype, shape-class, device, capability flags
- [ ] Implement cost model: per-kernel latency model (roofline: compute-bound vs. memory-bound estimate)
- [ ] Implement autotuning: candidate kernels benchmarked on calibration shapes, best-per-shape-class cached
- [ ] Implement heuristic selection: rule-based defaults (e.g., tiled GEMM for large, vectorized for small)
- [ ] Implement selection constraints: memory limits, deterministic-mode flag (disables autotuned variants)

**Implementation Requirements & Constraints:**
- Selection must be deterministic in deterministic mode; autotune cache keyed by (op, shape-class, device)
- Cost model must degrade gracefully: unknown kernels fall back to reference implementation with warning

**Engineering Milestones (DoD):**
- [ ] Autotuned selection beats heuristic baseline ≥ 15% on 80% of shape classes; selection runtime < 10 ms per graph
- [ ] Cost-model prediction within 20% of measured latency on 100 kernel/shape pairs

### 6.7 Backend Selection [x]
**Engineering Sub-tasks:**
- [ ] Implement backend capability negotiation: device availability, dtype support, memory budget, throughput probe
- [ ] Implement policy engine: user preference → capability filter → performance probe → decision
- [ ] Implement fallback chain: preferred backend → alternatives → CPU reference with per-op granularity
- [ ] Implement backend partitioning: assign graph regions to backends (heterogeneous placement) with transfer-cost estimation
- [ ] Implement selection report: chosen backend per region, rationale, transfer edges

**Implementation Requirements & Constraints:**
- Placement must minimize cross-backend transfers (transfer cost in cost model)
- Fallback must be automatic and observable (log + metric), never silent

**Engineering Milestones (DoD):**
- [ ] Policy selects capable backend in 100% of capability-matched cases; zero silent fallbacks (all logged)
- [ ] Heterogeneous placement reduces end-to-end latency ≥ 10% vs. single-backend on 2-device test rigs; transfer overhead within model ± 25%

### 6.8 Execution Planner [x]
**Engineering Sub-tasks:**
- [ ] Implement execution plan generation: topological schedule, parallel-ready sets, memory plan binding (Phase 2.13)
- [ ] Implement stream/queue assignment: op-to-stream mapping with dependency-aware ordering
- [ ] Implement plan cost estimation: latency (critical path + resource contention), peak memory, transfer volume
- [ ] Implement plan specialization: constant-folding pre-execution, buffer pre-allocation, warmup hints
- [ ] Implement plan caching: graph-hash → plan with invalidation on backend/capability change

**Implementation Requirements & Constraints:**
- Plan must be executable without further analysis (all deps, buffers, streams resolved)
- Plan cache must key on semantic graph hash (attribute-sensitive), not object identity

**Engineering Milestones (DoD):**
- [ ] Planned execution is deadlock-free in 100% of schedule simulations (10k graphs); plan cache hit rate ≥ 90% on repeated runs
- [ ] Estimated latency within 15% of measured; peak-memory estimate upper-bounds actual in 100% of runs

### 6.9 Code Generation [x]
**Engineering Sub-tasks:**
- [ ] Implement final lowering to executable units: kernel launch descriptors, tensor argument binding, constant inlining
- [ ] Implement register/thread mapping for target (CPU: vector-width tiling; future GPU: thread-block mapping annotations)
- [ ] Implement constant pool emission: deduplicated tensor constants with device placement
- [ ] Implement executable packaging: program object with entry points, symbol table, metadata (versions, checksums)
- [ ] Implement codegen verification: disassemble/dump path, instruction-count budget, semantic spot-checks

**Implementation Requirements & Constraints:**
- Generated code must be position-independent with respect to buffer addresses (indirect addressing only)
- Codegen output must be reproducible (deterministic ordering, no timestamps in output)

**Engineering Milestones (DoD):**
- [ ] Generated executables produce bit-identical results to interpreter on 500-program suite
- [ ] Codegen time < 1 s for 10k-node graphs; constant pool deduplication ≥ 40% on transformer models

### 6.10 Optimization Pipeline [x]
**Engineering Sub-tasks:**
- [ ] Implement pipeline orchestrator: ordered pass list, per-pass budget, conditional passes (by target/feature flags)
- [ ] Implement pass manager: run pass → verify → collect stats; rollback on verification failure
- [ ] Implement pipeline presets: `O0` (none), `O1` (quick), `O2` (default), `O3` (aggressive), `Os` (size)
- [ ] Implement pass instrumentation: per-pass time, node-delta, invocation count, failure reasons
- [ ] Implement pipeline dump: IR after each pass (optional), pipeline graph visualization, replay from any stage

**Implementation Requirements & Constraints:**
- Pipeline must be deterministic per preset + target; verification failure aborts with last-good IR
- Pass ordering constraints enforced (e.g., CSE before fusion, DCE after every mutation pass)

**Engineering Milestones (DoD):**
- [ ] O2 pipeline reduces op count ≥ 25% vs. O0 with ≤ 2× compile-time budget; verification rollback exercised in 100% of injected-failure tests
- [ ] Per-pass stats account for 100% of pipeline time; IR dumps reproduce identical outputs on replay

---

## PHASE 7 — RUNTIME (11 modules)

### 7.1 Scheduler [x]
**Engineering Sub-tasks:**
- [ ] Implement DAG scheduler: dependency tracking, in-degree counters, ready-queue dispatch
- [ ] Implement work-conserving policy: steal-able queues, priority classes (latency-critical vs. throughput)
- [ ] Implement batching: coalesce ready independent ops into batch dispatches (GPU-friendly)
- [ ] Implement preemption: cancellation propagation, priority inversion avoidance (priority inheritance)
- [ ] Implement scheduling metrics: queue depth, wait time, dispatch latency, utilization per worker

**Implementation Requirements & Constraints:**
- Scheduler must be lock-free on the common path (per-worker queues + Chase-Lev deques)
- Dependency decrement must be atomic; last-decrement wins ready-status (exactly-once dispatch)

**Engineering Milestones (DoD):**
- [ ] Zero double-dispatch / zero dropped tasks in 1M-task stress test; dispatch latency p99 < 50 µs
- [ ] Scheduler achieves ≥ 90% worker utilization on synthetic DAGs with ILP ≥ 4; preemption honored in 100% of cancel cases

### 7.2 Thread Pool [x]
**Engineering Sub-tasks:**
- [ ] Implement fixed-size pool: worker goroutines, task queues, graceful shutdown with drain semantics
- [ ] Implement dynamic pool: autoscale workers on queue depth (min/max bounds, hysteresis, cooldown)
- [ ] Implement task affinity: pin tasks to workers by data locality (NUMA-aware optional)
- [ ] Implement pool instrumentation: queue wait histogram, task latency, spawn/exit events, saturation alarms
- [ ] Implement panic isolation: worker panic → captured, wrapped, pool continues (no cascading loss)

**Implementation Requirements & Constraints:**
- Pool must support work-stealing across workers; shutdown must complete within timeout (default 30 s)
- Worker count default = GOMAXPROCS; oversubscription prohibited for CPU-bound pools

**Engineering Milestones (DoD):**
- [ ] Pool throughput ≥ 1M tasks/sec at 16 workers; panic isolation test: 100% of panics captured with 0 worker loss
- [ ] Autoscaling reacts within 100 ms of load change; graceful shutdown drains 100% of queued tasks

### 7.3 Async Runtime [x]
**Engineering Sub-tasks:**
- [ ] Implement future/promise type: state machine (Pending → Completed/Failed/Cancelled), `Await`, `Then`, `Wait`
- [ ] Implement async/await-style task scheduling over the thread pool with continuation passing
- [ ] Implement `Select`/`WaitAny`/`WaitAll` primitives with cancellation propagation
- [ ] Implement async I/O readiness integration (epoll/kqueue/IOCP) for network-backed ops
- [ ] Implement async diagnostics: pending-task dump, deadlock detection (cycle in await graph)

**Implementation Requirements & Constraints:**
- Futures must be single-use (consume-once semantics); double-await returns `ErrFutureConsumed`
- Continuations must not run on the completing thread by default (configurable inline-execution flag)

**Engineering Milestones (DoD):**
- [ ] Future state machine correct under 1M concurrent completions; `WaitAll`/`WaitAny` semantics verified on 1000-task suites
- [ ] Deadlock detector identifies 100% of induced await-cycles; async overhead ≤ 5 µs per continuation

### 7.4 Executor [x]
**Engineering Sub-tasks:**
- [ ] Implement graph executor: bind plan → allocate buffers → dispatch ops in schedule order → collect outputs
- [ ] Implement streaming execution: incremental op dispatch as inputs become ready (pipelined)
- [ ] Implement error propagation: op failure → cancel dependents → surface first-error with op context
- [ ] Implement executor hooks: pre/post op callbacks, tensor checkpointing at op boundaries
- [ ] Implement executor modes: eager (per-op), compiled (plan), interpret (fallback reference)

**Implementation Requirements & Constraints:**
- Executor must guarantee memory-plan discipline: buffers bound per plan, released on completion
- First-error semantics: exactly one error surfaces; dependent ops are cancelled, not executed

**Engineering Milestones (DoD):**
- [ ] Executor matches eager results bit-for-bit on 500 graphs in compiled mode; error propagation test: 100% of dependent ops cancelled on induced failure
- [ ] Streaming execution overlaps ≥ 60% of op latency on pipelined graphs; executor startup < 5 ms

### 7.5 Event Loop [x]
**Engineering Sub-tasks:**
- [ ] Implement reactor-style event loop: fd registration, readiness dispatch, timer wheel, idle handlers
- [ ] Implement event priorities and fairness: bounded time-slice per event class, starvation prevention
- [ ] Implement loop lifecycle: start/stop, graceful drain, cross-thread wakeup (self-pipe/eventfd)
- [ ] Implement event loop metrics: events/sec, latency per class, loop iterations, stall detection (> 100 ms stalls logged)
- [ ] Implement integration with async runtime and networking layer (Phase 17)

**Implementation Requirements & Constraints:**
- Event handlers must be non-blocking (documented contract); blocking handlers offloaded to pool
- Timer wheel must be O(1) insert/cancel; clock skew handled via monotonic clock

**Engineering Milestones (DoD):**
- [ ] Loop sustains ≥ 500k events/sec; stall detection fires within 10 ms of an injected 200 ms stall
- [ ] Timer accuracy within 1 ms p99 for 10k concurrent timers; zero lost wakeups in cross-thread test

### 7.6 Task Queue [x]
**Engineering Sub-tasks:**
- [ ] Implement MPMC queue: lock-free SPSC rings composed into MPMC, bounded/unbounded modes, backpressure
- [ ] Implement priority queue: heap-based with O(log n) push/pop, priority inversion mitigation
- [ ] Implement delayed/scheduled queue: timer-ordered, lazy promotion to ready queue
- [ ] Implement queue observability: depth gauges, enqueue/dequeue rates, wait-time histograms, saturation events
- [ ] Implement poison-message handling: retry policy (max attempts, exponential backoff), DLQ routing

**Implementation Requirements & Constraints:**
- Bounded queues must support blocking and non-blocking enqueue with `ErrQueueFull` policy
- Queue must preserve FIFO within a priority level; no starvation of lower priorities (aging)

**Engineering Milestones (DoD):**
- [ ] MPMC queue sustains ≥ 5M ops/sec aggregate at 32 threads; zero lost/torn messages in 100M-op run
- [ ] Priority ordering correct in 100% of 100k mixed-priority dequeues; DLQ receives 100% of exhausted poison messages

### 7.7 Runtime Profiler [x]
**Engineering Sub-tasks:**
- [ ] Implement sampling profiler: 100 Hz+ wall/CPU sampling with stack capture (runtime + native frames)
- [ ] Implement event-based profiling: op enter/exit, dispatch, wait, GC events into trace buffer
- [ ] Implement hotspot aggregation: self/total time per function, inclusive/exclusive, per-thread breakdown
- [ ] Implement hardware-counter integration (optional): cycles, cache misses, branch misses via perf event API
- [ ] Implement export: pprof, Chrome trace, collapsed-stack (flamegraph) formats

**Implementation Requirements & Constraints:**
- Sampling must be signal-safe (async-signal-safe stack walk) or use runtime-provided hooks
- Profiler memory is bounded: ring buffer with drop-counter for overflow

**Engineering Milestones (DoD):**
- [ ] Profile attribution error ≤ 5% vs. instrumented ground truth; CPU sampling overhead < 3%
- [ ] Flamegraph export of 30 s capture renders < 2 s; event traces cover 100% of dispatched ops in test harness

### 7.8 Runtime Debugger [x]
**Engineering Sub-tasks:**
- [ ] Implement breakpoint engine: op-level breakpoints (by op id/type), conditional predicates, hit counters
- [ ] Implement inspection API: pause/resume, step (op/into/out), tensor value dump, graph state snapshot
- [ ] Implement watchpoints: tensor value-change triggers with before/after capture
- [ ] Implement remote-debug protocol: attach/detach, control channel, data channel (chunked tensor transfer)
- [ ] Implement debugger safety: pause must not deadlock locks (quiescence analysis), resume is crash-safe

**Implementation Requirements & Constraints:**
- Debugger must operate on a paused execution snapshot; no live mutation of running ops
- Conditional predicates evaluated in sandboxed context (no side effects on program state)

**Engineering Milestones (DoD):**
- [ ] Breakpoints hit in 100% of placed cases; conditions evaluate correctly on 1000 predicate cases
- [ ] Pause-to-inspect latency < 100 ms; resume produces bit-identical continuation vs. uninterrupted run on 100 cases

### 7.9 Execution Tracing [x]
**Engineering Sub-tasks:**
- [ ] Implement distributed tracing hooks: span creation per op, context propagation (trace-id, span-id, parent)
- [ ] Implement trace context injection/extraction for cross-process boundaries (W3C TraceContext format)
- [ ] Implement trace sampling: head-based (rate) and tail-based (error/latency) with configurable policies
- [ ] Implement span annotations: attributes (shape, dtype, device), events (start, end, error), status codes
- [ ] Implement trace export: OTLP-compatible encoder, batching, and export backpressure handling

**Implementation Requirements & Constraints:**
- Trace context must propagate through async boundaries and task handoffs without loss
- Sampling decision made once at trace root; children inherit decision (consistent sampling)

**Engineering Milestones (DoD):**
- [ ] Span tree matches execution tree in 100% of traced runs; context propagation loss < 0.1% across process hops
- [ ] Tracing overhead ≤ 2% at 1% sampling; exporter survives 10× burst without blocking execution

### 7.10 Cancellation [x]
**Engineering Sub-tasks:**
- [ ] Implement cancellation token tree: parent → child propagation, token states (Active/Cancelled/Expired)
- [ ] Implement cooperative cancellation checkpoints: ops poll token at safe points (iteration boundaries)
- [ ] Implement forced cancellation: interruptible waits (context-aware), resource release on cancel
- [ ] Implement deadline propagation: remaining-time computation across call chains
- [ ] Implement cancellation semantics: `ErrCancelled` typed error, cleanup guarantees (deferred-release audit)

**Implementation Requirements & Constraints:**
- Cancellation must never leak: every registered resource has a release path on cancel
- Long-running ops must poll at least every 10 ms (or per-iteration) to honor cancel latency SLA

**Engineering Milestones (DoD):**
- [ ] Cancel propagation reaches all descendants in < 5 ms on 1000-task tree; zero leaked resources in cancel-stress test
- [ ] 100% of ops poll tokens at documented safe points (static analysis + runtime audit); `ErrCancelled` surfaces cleanly (no panic)

### 7.11 Kernel Registry [x]
**Engineering Sub-tasks:**
- [ ] Implement kernel registry: key = (op, dtype-set, device, arch), value = kernel descriptor + factory
- [ ] Implement registration API with conflict policy: duplicate-key → error or explicit override flag
- [ ] Implement kernel capability metadata: vectorization width, alignment requirements, memory footprint, determinism flag
- [ ] Implement registry query: best-match selection (subset dtype match, specificity ranking)
- [ ] Implement registry lifecycle: load (init), unload (deinit), hot-reload in dev mode with version check

**Implementation Requirements & Constraints:**
- Registration must be thread-safe (mutex or sync.Once per key); no unregistration of in-use kernels
- Kernel descriptors are immutable post-registration; mutations require new version id

**Engineering Milestones (DoD):**
- [ ] Registry lookup p99 < 1 µs; duplicate registration rejected in 100% of conflict cases (override requires explicit flag)
- [ ] Hot-reload swaps kernels without process restart in dev mode; 0 use-after-unload in lifecycle stress test

---

## PHASE 8 — CPU BACKEND (7 modules)

### 8.1 BLAS [x]
**Engineering Sub-tasks:**
- [ ] Implement BLAS Level 1: `Axpy`, `Dot`, `Nrm2`, `Scal`, `Swap`, `Copy` (vector ops, S/D/C/Z variants)
- [ ] Implement BLAS Level 2: `Gemv`, `Ger`, `Symv`, `Trmv`, `Tbsv` (matrix-vector with triangular/symmetric variants)
- [ ] Implement BLAS Level 3: `Gemm`, `Syrk`, `Trsm`, `Hemm` (matrix-matrix, blocked algorithms)
- [ ] Implement BLAS dispatcher: native (Go) → cgo (OpenBLAS/MKL) selection with feature detection and warmup
- [ ] Implement BLAS conformance test suite: reference comparisons across dtypes and edge shapes (transposed, non-square, batched)

**Implementation Requirements & Constraints:**
- cgo calls must hold no Go locks; GOMAXPROCS-aware thread binding for BLAS threads
- Non-contiguous inputs must be handled (copy-to-contiguous with layout flags)

**Engineering Milestones (DoD):**
- [ ] Conformance: 100% of Level 1–3 tests pass vs. reference (tolerance 1e-6 float32, 1e-12 float64) on 1000 shape cases
- [ ] DGEMM ≥ 70% of peak theoretical FLOPs on AVX2 host; dispatcher adds < 2 µs overhead per call

### 8.2 GEMM [x]
**Engineering Sub-tasks:**
- [ ] Implement GEMM micro-kernel: register-blocked inner loops (MR×NR tiles), FMA chains, vectorized loads/stores
- [ ] Implement GEMM packing: A/B panel packing into contiguous buffers (transA/transB handling)
- [ ] Implement macro-kernel: block factorization (MC×KC×NC) tuned to cache hierarchy (L1/L2/L3 sizes auto-detected)
- [ ] Implement GEMM variants: bias-add, ReLU fusion, transposed outputs, batched GEMM (strided)
- [ ] Implement GEMM auto-tuning: cache-block size search per machine, stored in per-host tuning file

**Implementation Requirements & Constraints:**
- Micro-kernel must be cache-oblivious-correct with explicit tiling for L2/L3; register tiles sized to vector width
- Thread-parallel GEMM must be deterministic (fixed partitioning) when deterministic flag set

**Engineering Milestones (DoD):**
- [ ] GEMM correctness vs. reference on 500 (M,N,K) combinations incl. edge cases (1×N, M×1, K=0); rel. error < 1e-6 (fp32)
- [ ] Single-thread SGEMM ≥ 80% of roofline on AVX2; multi-thread scaling efficiency ≥ 85% at 8 cores

### 8.3 SIMD [x]
**Engineering Sub-tasks:**
- [ ] Implement SIMD abstraction layer: portable vector types (256/512-bit), intrinsic wrappers per ISA (SSE/AVX/AVX2/AVX-512/Neon)
- [ ] Implement kernel library: `Load/Store` (aligned/unaligned), arithmetic, FMA, comparisons, horizontal reductions, gathers
- [ ] Implement masked operations: blend/select patterns, predicate generation, tail-mask handling
- [ ] Implement ISA dispatch: CPUID detection → function-pointer table, with runtime verification (cpuid vs. OS support via XGETBV)
- [ ] Implement SIMD test harness: known-answer tests per intrinsic, alignment torture tests, ISA-emulation fallback tests

**Implementation Requirements & Constraints:**
- All SIMD kernels must have scalar fallbacks; no ISA assumption without runtime check
- SIMD code must be memory-safe: no reads past tensor bounds including tail loads (masked/scalar tail)

**Engineering Milestones (DoD):**
- [ ] 100% of SIMD kernels pass known-answer tests on all supported ISAs; 0 segfaults in 1M alignment-randomized runs
- [ ] SIMD kernels ≥ 8× scalar on 256-bit for elementwise float32; dispatch table resolution at init (< 1 ms)

### 8.4 Vectorized Kernels [x]
**Engineering Sub-tasks:**
- [ ] Implement vectorized elementwise kernels: unary (exp, log, tanh, sigmoid, erf) and binary (add, mul, min, max, pow)
- [ ] Implement vectorized reduction kernels: sum/max/min with SIMD partial accumulators and tree combine
- [ ] Implement vectorized tensor transforms: transpose tiles, pack/unpack, cast kernels (f32↔f16, f32↔bf16 with round-to-nearest-even)
- [ ] Implement vectorized normalization: layernorm/RMSNorm fused (mean+var+scale+shift in one pass, Welford)
- [ ] Implement kernel parameterization: vector-width-agnostic source (compile-time width constants)

**Implementation Requirements & Constraints:**
- Transcendental kernels must meet accuracy target: ≤ 2 ULP (exp/log), ≤ 4 ULP (tanh) vs. libm
- Fused normalization must use Welford or two-pass for numerical stability

**Engineering Milestones (DoD):**
- [ ] Accuracy verified vs. libm reference on 10M random inputs per function; layernorm matches reference < 1e-5 rel. error
- [ ] Throughput: elementwise ≥ 10 GB/s per core; layernorm ≥ 3× naive implementation on 4096-dim vectors

### 8.5 Thread Parallelism [x]
**Engineering Sub-tasks:**
- [ ] Implement parallel-for: range splitting (contiguous chunks, interleaved), grain-size heuristics, nested-parallelism control
- [ ] Implement NUMA-aware allocation: first-touch policy option, node-affinity hints for large tensors
- [ ] Implement parallel reductions: per-thread accumulators, associative combine, deterministic ordering option
- [ ] Implement thread oversubscription guard: detect nested parallel regions, collapse to sequential when small
- [ ] Implement parallelism metrics: parallel efficiency, load-imbalance estimate, spin-wait vs. yield policy tuning

**Implementation Requirements & Constraints:**
- Parallel-for must be deterministic in deterministic mode (fixed chunk assignment, ordered combines)
- Grain size auto-tuned: parallelism only when work ≥ 10 µs estimated

**Engineering Milestones (DoD):**
- [ ] Scaling efficiency ≥ 80% at 8 threads on memory-bound and compute-bound benchmarks; zero race conditions under `-race` on all parallel kernels
- [ ] Deterministic mode produces bit-identical results across 1/2/4/8 threads on 100 kernels; oversubscription guard activates in 100% of nested-small cases

### 8.6 Cache Optimization [x]
**Engineering Sub-tasks:**
- [ ] Implement cache-aware tiling: tile sizes derived from detected cache hierarchy (L1/L2/L3 sizes, line size 64B)
- [ ] Implement prefetching: software prefetch instructions at tuned distances for streaming kernels
- [ ] Implement layout optimization: tile-transpose storage for repeated access patterns, channel-last/channel-first auto-selection
- [ ] Implement cache blocking for GEMM/conv/reduce with block-size search per op class
- [ ] Implement cache-optimization validation: perf-counter profiling (miss rates) on target hardware

**Implementation Requirements & Constraints:**
- Tile sizes must adapt at runtime (CPU detection); hardcoded sizes forbidden
- Prefetch distance must be tunable; wrong prefetch can degrade (A/B measured per kernel)

**Engineering Milestones (DoD):**
- [ ] L2 miss rate ≤ 5% on tiled GEMM 4096² fp32; prefetching improves kernel throughput ≥ 10% on ≥ 60% of kernels
- [ ] Cache hierarchy auto-detection correct on 10 emulated CPUID profiles; layout auto-selection beats fixed layout ≥ 15% on 50% of benchmarks

### 8.7 Kernel Registry (CPU) [x]
**Engineering Sub-tasks:**
- [ ] Implement CPU kernel catalog: per-op kernel table with ISA requirements, dtype matrix, shape-class ranges
- [ ] Implement dispatch resolution: (op, dtype, shape-class, device) → best kernel with specificity ranking
- [ ] Implement kernel benchmarking harness: calibration shapes, warmup, statistical timing, ranking
- [ ] Implement kernel fallback chains: AVX-512 → AVX2 → SSE → scalar, automatic on CPUID or runtime SIGILL recovery
- [ ] Implement registry persistence: per-host best-kernel cache file with invalidation on CPU change

**Implementation Requirements & Constraints:**
- Dispatch must not regress: selected kernel must pass conformance before promotion to default
- SIGILL recovery (illegal instruction on older CPU) must fall back and re-run without data loss

**Engineering Milestones (DoD):**
- [ ] Dispatch selects optimal kernel in ≥ 95% of shape classes (vs. exhaustive autotune); dispatch latency < 500 ns
- [ ] Fallback chain exercised on 100% of ISA tiers in emulation; persistent cache reduces selection time ≥ 90% on second run

---

## PHASE 9 — GPU BACKEND (FUTURE) (6 modules)

### 9.1 CUDA [x]
**Engineering Sub-tasks:**
- [ ] Design CUDA backend interface: device context, stream management, event synchronization, module loading (PTX/CUBIN)
- [ ] Implement memory management: device allocator (buddy/pool), host↔device transfer (pinned staging buffers), unified-memory policy
- [ ] Implement kernel launch abstraction: grid/block mapping, shared-memory sizing, launch-bounds metadata
- [ ] Implement cuBLAS/cuDNN interop paths for GEMM/conv with fallback to custom kernels
- [ ] Implement CUDA error handling: async error polling, ECC/timeout detection, context reset protocol

**Implementation Requirements & Constraints:**
- CUDA backend is forward-gated: interfaces defined now, implementation gated on hardware availability
- All async operations must be stream-ordered; default stream must not be used for concurrent ops

**Engineering Milestones (DoD):**
- [ ] Interface compiles and mocks pass on CPU-only CI (simulated device); contract tests define expected behavior for 50 ops
- [ ] On real hardware: memory transfer ≥ 80% of PCIe bandwidth; kernel launch overhead < 5 µs

### 9.2 ROCm [x]
**Engineering Sub-tasks:**
- [ ] Design ROCm/HIP backend: port CUDA interface via HIP mapping layer (hipMalloc/hipLaunchKernel)
- [ ] Implement AMD-specific tuning: wavefront sizing (32/64), LDS (local memory) allocation, MFMA instruction paths
- [ ] Implement MIOpen interop for conv/normalization with fallback strategy
- [ ] Implement ROCm device management: agent enumeration (ROCR), topology (NUMA/PCIe), clock/memory metrics
- [ ] Implement dual-backend build tags: `rocm` vs. `cuda` with shared test harness

**Implementation Requirements & Constraints:**
- HIP path must maintain source compatibility with CUDA interface (single source where feasible)
- Kernel code must be compilable by both NVCC and HIPCC via shared header macros

**Engineering Milestones (DoD):**
- [ ] HIP backend passes same conformance suite as CUDA on matched hardware (when available); mock tests pass on CPU-only CI
- [ ] Build-time selection is clean: `rocm` tag produces no CUDA dependencies (linkage audit)

### 9.3 Vulkan [x]
**Engineering Sub-tasks:**
- [ ] Design Vulkan compute backend: instance/device selection, queue families, command buffers, fences/semaphores
- [ ] Implement descriptor-set management: tensor bindings (storage buffers), push constants for small params
- [ ] Implement SPIR-V pipeline: shader module compilation cache, pipeline layout cache, specialization constants
- [ ] Implement memory management: Vulkan memory allocator (pool/arena over vkAllocateMemory), host-visible staging
- [ ] Implement validation-layer integration in dev builds (sync checks, memory checks)

**Implementation Requirements & Constraints:**
- Vulkan backend must be portable across vendors (no vendor extensions in core path)
- Explicit synchronization: all resource barriers documented per kernel (no implicit ordering)

**Engineering Milestones (DoD):**
- [ ] Mock/simulated-device tests pass on CPU-only CI; contract tests cover 50 ops
- [ ] On hardware: compute dispatch overhead < 10 µs; synchronization correct under validation layer (zero errors)

### 9.4 Metal [x]
**Engineering Sub-tasks:**
- [ ] Design Metal backend: device/queue abstraction, command buffer encoding, argument buffers
- [ ] Implement MTLFunction library management: precompiled metallib, runtime function lookup, pipeline state cache
- [ ] Implement memory model mapping: managed/shared/private storage modes per tensor lifetime
- [ ] Implement Metal Performance Shaders (MPS) interop for matmul/conv with fallback kernels
- [ ] Implement Apple Silicon specifics: unified memory policy, tile-based rasterization hints for compute

**Implementation Requirements & Constraints:**
- Metal backend gated to macOS/arm64 builds (build tag `metal`); no-op stub elsewhere
- Command buffer commits must be tracked for outstanding-count backpressure

**Engineering Milestones (DoD):**
- [ ] Stub builds pass on non-macOS CI; macOS contract tests define behavior for 50 ops
- [ ] On Apple Silicon: unified-memory copies avoided for ≥ 90% of resident tensors; pipeline cache hit rate ≥ 95%

### 9.5 OpenCL [x]
**Engineering Sub-tasks:**
- [ ] Design OpenCL backend: platform/device enumeration, context, command queues (out-of-order mode)
- [ ] Implement program build pipeline: source → binary cache, build-options per device, build-log capture
- [ ] Implement buffer/sub-buffer management: pinned host buffers, zero-copy (CL_MEM_USE_HOST_PTR) paths
- [ ] Implement kernel argument binding: scalar args, buffer args, local-memory sizing
- [ ] Implement device-partitioning: sub-device creation for multi-queue overlap

**Implementation Requirements & Constraints:**
- OpenCL path must tolerate driver quirks: work-group size queries respected, extension gating
- Kernel source must target OpenCL C 1.2 baseline with 2.0 optional extensions

**Engineering Milestones (DoD):**
- [ ] CPU-device tests pass (POCL) on CI; contract tests cover 50 ops; driver-quirk suite passes on 10 emulated devices
- [ ] Out-of-order queues yield ≥ 1.2× throughput on pipelined workloads; build cache reduces compile ≥ 80% on repeat

### 9.6 WebGPU
**Engineering Sub-tasks:**
- [ ] Design WebGPU backend: adapter/instance selection, device limits query, queue submission
- [ ] Implement WGSL pipeline: shader generation from op IR, bind-group layout mapping, pipeline cache
- [ ] Implement buffer management: mapped-at-create buffers, staging buffers, onSubmittedWorkDone tracking
- [ ] Implement browser/edge deployment path: WASM host integration, async API bridging (promises → futures)
- [ ] Implement limits adaptation: min/max buffer sizes, uniform limits, subgroup size handling

**Implementation Requirements & Constraints:**
- WebGPU backend must be fully async (no blocking calls); futures bridge the async API
- Shader generation must respect WebGPU validation rules (binding limits, alignment)

**Engineering Milestones (DoD):**
- [ ] Contract tests define behavior for 50 ops; WASM host integration demo executes a fused kernel in browser harness
- [ ] Submission overhead < 20 µs per batch; zero validation errors on generated WGSL for supported op set

---

## PHASE 10 — MODEL ENGINE (12 modules)

### 10.1 Sequential API [x]
**Engineering Sub-tasks:**
- [ ] Implement `Sequential` container: ordered layer list, `Add`, `Insert`, `Remove`, `Pop`, `Clear`
- [ ] Implement forward chaining: output of layer N feeds layer N+1, shape propagation at build time
- [ ] Implement `Sequential` as callable: `Forward(x)` with input/output validation, multi-input/output support
- [ ] Implement parameter aggregation: `Parameters()`, `TrainableParameters()`, nested module recursion
- [ ] Implement serialization of Sequential: layer configs, weights, construction-from-config

**Implementation Requirements & Constraints:**
- Shape propagation must be eager: incompatible layer chain fails at `Add` time, not at forward
- Sequential must be immutable during forward (concurrent-run safe for inference, single-writer for training)

**Engineering Milestones (DoD):**
- [ ] Shape errors caught at build time in 100% of malformed chains (100 cases); forward matches manual composition bit-for-bit on 200 models
- [ ] Parameter aggregation correct on 100 nested-module suite; serialization round-trip preserves outputs

### 10.2 Functional API [x]
**Engineering Sub-tasks:**
- [ ] Implement functional model definition: `Input` placeholders, op-composition graph, multi-branch topology
- [ ] Implement DAG-based forward: topological execution of composed ops, shared-subgraph reuse
- [ ] Implement model surgery: layer freezing, branch insertion, subgraph extraction (`Model(inputs, outputs)`)
- [ ] Implement functional training integration: gradient flow through arbitrary DAGs, shared weights
- [ ] Implement functional model validation: single-output/ multi-output, unused-input detection

**Implementation Requirements & Constraints:**
- Functional models must support arbitrary DAGs (residual, inception, multi-head) — no tree restriction
- Shared tensors must be versioned to prevent accidental in-place mutation during training

**Engineering Milestones (DoD):**
- [ ] Functional API expresses ResNet/Transformer topologies verified against Sequential equivalents (same outputs)
- [ ] DAG forward handles 1000-op graphs; gradient correctness on 200 random DAGs (finite-difference check)

### 10.3 Layers [x]
**Engineering Sub-tasks:**
- [ ] Implement core layers: `Dense`, `Conv1d/2d/3d`, `BatchNorm`, `LayerNorm`, `GroupNorm`, `RNN`, `LSTM`, `GRU`, `Embedding`, `Dropout`
- [ ] Implement layer init schemes: `GlorotUniform`, `HeNormal`, `Orthogonal`, `Constant`, per-layer defaults
- [ ] Implement layer serialization: config (JSON), weights, `FromConfig` reconstruction
- [ ] Implement layer composability: `Sequential`-compatibility, multi-call statefulness (RNN states)
- [ ] Implement layer parameter inspection: shapes, dtypes, sparsity report per layer

**Implementation Requirements & Constraints:**
- Init schemes must be deterministic given seed; variance formulas match theory (fan-in/fan-out)
- Conv layers must support padding/stride/dilation groups with shape inference at construction

**Engineering Milestones (DoD):**
- [ ] All layers match reference (NumPy/PyTorch-equivalent) forward outputs on 100 seeded cases per layer type
- [ ] Init variance within 2% of theoretical on 10k samples; serialization round-trip: 100% of layers reconstruct with identical outputs

### 10.4 Activations [x]
**Engineering Sub-tasks:**
- [ ] Implement activation set: `ReLU`, `LeakyReLU`, `GELU` (exact + tanh-approx), `SiLU/Swish`, `Mish`, `ELU`, `SELU`, `Softmax`, `LogSoftmax`, `Sigmoid`, `Tanh`, `SwiGLU`
- [ ] Implement in-place variants with autograd-correctness guards (leaf-protection)
- [ ] Implement derivative/Jacobian support for each activation (analytic, vectorized)
- [ ] Implement numerically stable variants: `LogSoftmax` (max-shift), `Softmax` (max-shift), `GELU` (polynomial bounds)
- [ ] Implement activation benchmarks: throughput per activation, SIMD coverage report

**Implementation Requirements & Constraints:**
- Softmax must be max-shifted to prevent overflow; log-sum-exp stability required
- In-place activations forbidden on tensors required for backward (alias check)

**Engineering Milestones (DoD):**
- [ ] Activations match scipy/torch reference within 1e-6 on 10M-point sweeps incl. extreme values (±100)
- [ ] Derivatives verified against finite differences on 1000 points per activation; SIMD kernels ≥ 8× scalar

### 10.5 Loss Functions [x]
**Engineering Sub-tasks:**
- [ ] Implement loss set: `MSE`, `MAE`, `CrossEntropy` (with logits, label-smoothing), `NLL`, `BCE`, `BCEWithLogits`, `Huber`, `KLDiv`, `CosineSimilarity`, `CTCLoss`
- [ ] Implement reduction modes: `mean`, `sum`, `none` (per-element), weighted variants
- [ ] Implement gradient correctness: analytic gradients for every loss, verified vs. autograd
- [ ] Implement numerical stability: log-space computation for likelihood losses, epsilon guards for log(0)
- [ ] Implement loss composition: weighted sums, multi-task loss with per-task scaling

**Implementation Requirements & Constraints:**
- CrossEntropy must fuse log-softmax + NLL for stability (no intermediate overflow)
- Loss functions must accept class weights with shape validation

**Engineering Milestones (DoD):**
- [ ] Losses match reference within 1e-6 on 1000-case suite incl. edge cases (single class, zero weights, extreme logits)
- [ ] Gradients match finite differences (rel. error < 1e-5) on 100% of loss×reduction combinations

### 10.6 Optimizers [x]
**Engineering Sub-tasks:**
- [ ] Implement optimizer set: `SGD` (+momentum, nesterov), `Adam`, `AdamW`, `RMSProp`, `Adagrad`, `Adadelta`, `Lion`, `SGDW`
- [ ] Implement state management: per-parameter state buffers (m, v), lazy init, state serialization
- [ ] Implement parameter-group semantics: per-group lr/weight-decay/betas, gradient centralization option
- [ ] Implement weight decay decoupling (AdamW) and gradient clipping (norm/value) hooks
- [ ] Implement optimizer step determinism: fixed update order, reproducible given seed and schedule

**Implementation Requirements & Constraints:**
- Optimizer state must be allocated from tensor pool; state dtype follows mixed-precision policy
- Weight decay applied to gradients (L2) vs. parameters (decoupled) must be explicitly selected, never implicit

**Engineering Milestones (DoD):**
- [ ] Optimizers match reference trajectory on 100 seeded convex problems (final loss within 1e-8); AdamW decay semantics verified (no L2 coupling)
- [ ] Step latency ≤ 2× parameter count throughput (10M params < 20 ms); state round-trip serialization lossless

### 10.7 Checkpoints [x]
**Engineering Sub-tasks:**
- [ ] Implement checkpoint format: header (format version, model config), tensor table (name → shape/dtype/offset), optimizer state, RNG state, metadata
- [ ] Implement save/load with atomic write (temp file + rename), fsync durability option
- [ ] Implement sharded checkpoints: per-tensor shards, index file, parallel save/load
- [ ] Implement checkpoint resume: full state restoration (model + optimizer + scheduler + step count), exact-restart verification
- [ ] Implement checkpoint management: retention policy (keep-last-N, keep-best-by-metric), pruning, integrity verification (checksums)

**Implementation Requirements & Constraints:**
- Checkpoint save must not block training > 50 ms p99 (async flush to background task)
- Resume must be bit-exact: resumed training continues identical trajectory (same RNG state)

**Engineering Milestones (DoD):**
- [ ] Resume-after-save produces identical training trajectory (bit-exact loss curve) on 50 training runs
- [ ] Sharded save/load scales linearly: 1B-parameter checkpoint I/O ≥ 1 GB/s; checksum detects 100% of corruption injections

### 10.8 Mixed Precision [x]
**Engineering Sub-tasks:**
- [ ] Implement autocast policy: op-level dtype casting rules (fp32→bf16/fp16 whitelist, fp32-req blacklist)
- [ ] Implement loss scaling (for fp16): dynamic scaler (growth/backoff factors, interval), scale-unwrap on gradients
- [ ] Implement master-weight maintenance: fp32 copies for fp16 params, update path
- [ ] Implement gradient casting: downcast on backward, upcast on accumulate, overflow detection (Inf/NaN in gradients)
- [ ] Implement precision telemetry: per-op dtype histogram, overflow counters, speedup report

**Implementation Requirements & Constraints:**
- Loss scaling must prevent gradient underflow: scale factor adapts to overflow history
- Autocast must be scope-based (`with Autocast()`) with nesting and override rules

**Engineering Milestones (DoD):**
- [ ] Mixed-precision training converges to within 0.1% of fp32 baseline on 5 model benchmarks; zero un-scaled overflows in 100 epochs
- [ ] Speedup ≥ 1.5× on tensor-heavy layers (benchmarked); overflow detection catches 100% of injected Inf gradients

### 10.9 Quantization [x]
**Engineering Sub-tasks:**
- [ ] Implement quantization schemes: dynamic (int8), static (calibration-based), QAT (fake-quant training), int4/uint4 packing
- [ ] Implement quantization math: affine (scale + zero-point), symmetric, per-tensor/per-channel granularity
- [ ] Implement calibration: min-max, percentile, MSE-optimal, KL-divergence methods on representative datasets
- [ ] Implement quantized kernels: int8 GEMM (dot-product accumulation), quantized conv, requantization
- [ ] Implement quantization-aware export: QDQ (quantize-dequantize) annotation for ONNX interchange

**Implementation Requirements & Constraints:**
- Quantization must declare error bounds (max/mean abs error) per tensor; violation fails export
- QAT fake-quant must be differentiable (STE — straight-through estimator)

**Engineering Milestones (DoD):**
- [ ] Post-training int8 quantization: accuracy drop ≤ 1% on 5 model benchmarks; int8 GEMM ≥ 2× fp32 throughput on CPU (AVX2/VNNI)
- [ ] Calibration error within declared bounds on 100% of calibrated tensors; QAT recovers ≥ 90% of fp32 accuracy on 3 benchmarks

### 10.10 LoRA [x]
**Engineering Sub-tasks:**
- [ ] Implement LoRA layer: frozen base weight W₀ + trainable low-rank update B·A (rank r, alpha scaling)
- [ ] Implement initialization: A ~ Kaiming, B = 0 (zero-init update), alpha/r scaling at forward
- [ ] Implement merge/unmerge: W = W₀ + (alpha/r)·B·A for inference, exact unmerge restore
- [ ] Implement adapter-only training: parameter isolation (only A/B trainable), state dict with adapter keys
- [ ] Implement multi-adapter serving: hot-swappable adapters per request, adapter registry

**Implementation Requirements & Constraints:**
- Base weights must remain bit-identical during LoRA training (freeze verification)
- Merge must be exact: merged forward ≡ unmerged forward (bitwise, same dtype)

**Engineering Milestones (DoD):**
- [ ] LoRA fine-tune matches full-fine-tune within 0.5% task accuracy on 3 benchmarks at r=8; trainable param count ≤ 1% of base
- [ ] Merge/unmerge round-trip bit-exact on 100 cases; base-weight freeze verified (checksum) on 100% of training steps

### 10.11 ONNX Import [x]
**Engineering Sub-tasks:**
- [ ] Implement ONNX protobuf parser: model/graph/node/attribute/tensor proto decoding
- [ ] Implement op mapping: ONNX ops → engine ops (≥ 100 ops), attribute translation, shape inference from ONNX shapes
- [ ] Implement graph reconstruction: ONNX graph → Graph IR with initializer/input/output binding
- [ ] Implement unsupported-op handling: fallback registry (custom-op registration), partial-import with error report
- [ ] Implement import validation: forward-pass equivalence check vs. ONNX Runtime reference outputs

**Implementation Requirements & Constraints:**
- Import must handle ONNX opset versioning (per-node opset) with explicit unsupported-version errors
- Constant initializers must be converted to engine constants (folding-ready)

**Engineering Milestones (DoD):**
- [ ] Import ≥ 100 ONNX ops; 50 reference models (ResNet/BERT-class) import with zero unsupported ops
- [ ] Imported-model outputs match ONNX Runtime within 1e-4 on 100% of reference inputs; import time < 30 s for 1B-param models

### 10.12 ONNX Export [x]
**Engineering Sub-tasks:**
- [ ] Implement graph → ONNX exporter: node emission, attribute encoding, initializer extraction, input/output value-info
- [ ] Implement exporter tracing: record ops during forward (tracer mode) with tensor-value specialization
- [ ] Implement exporter scripting: control-flow export via IR analysis (no tracing for dynamic shapes)
- [ ] Implement export verification: reload exported model, compare outputs vs. source (round-trip test)
- [ ] Implement export metadata: opset selection, producer info, documentation strings, external-data tensors (>2GB)

**Implementation Requirements & Constraints:**
- Export must produce valid ONNX (onnx.checker passes) for every supported graph
- Dynamic shapes must export with symbolic dims, not baked-in batch sizes

**Engineering Milestones (DoD):**
- [ ] Exported models pass `onnx.checker` on 100% of export corpus (100 graphs); round-trip output match within 1e-5 on 100%
- [ ] External-data export handles 10GB models; symbolic dims preserved (batch-size flexibility verified on reload)

---

## PHASE 11 — INFERENCE (8 modules)

### 11.1 Tokenizer [x]
**Engineering Sub-tasks:**
- [ ] Implement tokenizer backends: BPE (byte-level), WordPiece, SentencePiece (Unigram/BPE), Word level, Byte fallback
- [ ] Implement vocabulary loading: merges/rules file parsing, special-token table, added-token handling (priority rules)
- [ ] Implement encoding: pre-tokenization regex, merge application, OOV → byte-fallback/UNK policy, offsets/spans
- [ ] Implement decoding: token ids → text, byte-repair, special-token skip, round-trip verification
- [ ] Implement fast path: SIMD/parallel batch encoding, tokenizer caching (input-hash → ids)

**Implementation Requirements & Constraints:**
- Tokenizer must be deterministic and thread-safe; no mutable state per encode
- Special tokens must never be merged/split; added-token precedence over base merges

**Engineering Milestones (DoD):**
- [ ] Encode/decode round-trip: 100% of 100k corpus sentences recoverable (byte-exact for byte-BPE)
- [ ] Throughput ≥ 1MB text/sec encode; cache hit rate ≥ 60% on repeated-input workload; matches HF tokenizer outputs on 10k comparison cases

### 11.2 KV Cache [x]
**Engineering Sub-tasks:**
- [ ] Implement KV cache structure: per-layer, per-head key/value tensors with sequence-length indexing
- [ ] Implement cache management: pre-allocation (max-seq policy), growth (append policy), sliding-window eviction
- [ ] Implement paged attention layout: block-table mapping, block-size tuning, copy-on-append
- [ ] Implement cache quantization: fp8/int8 KV with per-channel scales, dequant on attention
- [ ] Implement cache metrics: utilization, hit/miss, memory footprint, reuse across requests (prefix caching)

**Implementation Requirements & Constraints:**
- Cache must guarantee correctness: position ids consistent with cached entries (RoPE position handling)
- Prefix caching requires exact prefix match (hash of token ids + position encoding config)

**Engineering Milestones (DoD):**
- [ ] Cached-attention outputs bit-identical to non-cached on 100 generation cases (all positions)
- [ ] Paged layout reduces memory waste ≤ 4% (block-boundary loss); prefix cache hit rate ≥ 30% on multi-turn workload; fp8 KV within 0.1% accuracy on 5 models

### 11.3 Beam Search [x]
**Engineering Sub-tasks:**
- [ ] Implement beam search: beam-width parameterization, score normalization (length penalty, coverage penalty)
- [ ] Implement beam state management: hypotheses, finished set, early-stop policy (no-improvement threshold)
- [ ] Implement diversity mechanisms: diverse beam search (group penalty), temperature per beam
- [ ] Implement batched beam search: beam-major batching, padding/mask handling, ragged batch assembly
- [ ] Implement beam search tracing: hypothesis tree export, per-step score table

**Implementation Requirements & Constraints:**
- Beam search must be deterministic given seed and width; ties broken by token id
- Length normalization must be applied consistently across hypotheses (comparable scores)

**Engineering Milestones (DoD):**
- [ ] Beam search finds optimal sequence (brute-force verified) for width ≥ target on 100 small cases
- [ ] Batched beam search ≥ 3× single-batch throughput at batch 32; zero non-termination in 1000 runs (max-length enforced)

### 11.4 Top-K [x]
**Engineering Sub-tasks:**
- [ ] Implement Top-K selection: partial-sort (introselect), heap-based K extraction, tie-breaking by index
- [ ] Implement batched Top-K: per-row independent, vectorized comparison kernels
- [ ] Implement Top-K + sampling integration: distribution over K tokens, temperature scaling pre-selection
- [ ] Implement K-adaptive selection: dynamic K by entropy threshold
- [ ] Implement Top-K validation: K bounds (1 ≤ K ≤ vocab), probability renormalization

**Implementation Requirements & Constraints:**
- Top-K must be O(n log k) worst-case; exact (not approximate) by default
- Ties must resolve deterministically (lowest index first)

**Engineering Milestones (DoD):**
- [ ] Top-K results identical to full-sort reference on 10k random distributions (incl. all-tie cases)
- [ ] Throughput ≥ 500M elements/sec (fp32, AVX2); K=1 special case uses argmax fast path (≥ 2× general path)

### 11.5 Top-P (Nucleus) [x]
**Engineering Sub-tasks:**
- [ ] Implement nucleus sampling: sorted cumulative probabilities, threshold cut at p, renormalization
- [ ] Implement combined Top-K + Top-P filtering pipeline with ordering guarantees
- [ ] Implement cumulative-sum kernel: SIMD prefix-sum with sorted-input optimization
- [ ] Implement edge handling: min-1-token guarantee, min-probability floor, all-tokens-excluded fallback
- [ ] Implement sampling integration: categorical sampling over filtered set with seedable RNG

**Implementation Requirements & Constraints:**
- Top-P must sort descending (cost O(n log n)) or use partial selection + post-filter for p > 0.9
- Renormalization must be exact (sum to 1 within 1e-6)

**Engineering Milestones (DoD):**
- [ ] Filtered distribution mass within 1e-6 of p on 10k distributions; min-token guarantee holds in 100% of edge cases
- [ ] Top-P path latency ≤ 2× Top-K path; RNG sampling distribution chi-square test passes (p > 0.01) on 1M samples

### 11.6 Streaming [x]
**Engineering Sub-tasks:**
- [ ] Implement streaming inference: incremental token emission (token-by-token channel/stream API)
- [ ] Implement chunked input processing: windowed context with overlap policy, position continuity
- [ ] Implement backpressure: consumer-paced emission, bounded buffers, slow-consumer handling
- [ ] Implement stream interruption: stop-sequences (multi-token, case/whitespace variants), cancel mid-generation
- [ ] Implement stream telemetry: tokens/sec, time-to-first-token (TTFT), inter-token latency (ITL) histograms

**Implementation Requirements & Constraints:**
- Streaming must not degrade quality: identical outputs to non-streaming for same seed (verified)
- Stop-sequence detection must handle cross-chunk boundary matches

**Engineering Milestones (DoD):**
- [ ] Streaming vs. batch outputs bit-identical on 100 cases; stop-sequences detected within 1 token of match position in 100% of tests
- [ ] TTFT p95 < 200 ms on reference model; ITL p95 < 50 ms; zero deadlock under slow-consumer test

### 11.7 Dynamic Batching [x]
**Engineering Sub-tasks:**
- [ ] Implement request aggregation: time-window (micro-batch) and size-threshold triggers
- [ ] Implement batch assembly: ragged sequences → padded batch with attention masks, length sorting
- [ ] Implement batch execution: single forward over batch, per-request output splitting
- [ ] Implement continuous batching: iteration-level admission/eviction (finished requests exit, new enter)
- [ ] Implement batch scheduling policies: max-batch-size, max-total-tokens, priority-weighted admission

**Implementation Requirements & Constraints:**
- Padding tokens must be masked in attention (no information leakage between requests)
- Batching must be bounded by memory: pre-flight KV-cache budget check

**Engineering Milestones (DoD):**
- [ ] Batched outputs identical to single-request outputs (bit-exact) on 100 cases; throughput ≥ 2.5× at batch 16 vs. batch 1
- [ ] Continuous batching sustains ≥ 90% GPU/utilization on Poisson arrival load; memory budget never exceeded in stress test

### 11.8 Request Scheduler [x]
**Engineering Sub-tasks:**
- [ ] Implement request queue: priority classes (SLA tiers), FIFO within class, aging to prevent starvation
- [ ] Implement admission control: token-budget, concurrency-limit, memory-budget gates with rejection policy
- [ ] Implement scheduling policies: FCFS, SJF (shortest-job-first by prompt length), priority preemption
- [ ] Implement fairness: per-tenant/per-priority token-rate limits (token bucket), deficit scheduling
- [ ] Implement scheduler observability: queue depth, wait-time percentiles, admission/rejection rates, SLA-violation alarms

**Implementation Requirements & Constraints:**
- Preemption must be cooperative: request yields at safe boundary (iteration end)
- Rejection must be explicit and observable (`ErrCapacity` with retry-after hint)

**Engineering Milestones (DoD):**
- [ ] SLA attainment ≥ 99% for p50/p95 targets on synthetic load (10k requests); starvation-free under adversarial priority mix
- [ ] Fairness: per-tenant throughput within 5% of fair share under 10× load imbalance; rejection rate ≤ 1% at 90% capacity

---

## PHASE 12 — DISTRIBUTED SYSTEMS (8 modules)

### 12.1 RPC [x]
**Engineering Sub-tasks:**
- [ ] Implement RPC framework: request/response serialization (msgpack/protobuf), method dispatch table
- [ ] Implement transport abstraction: TCP/TLS, Unix socket, in-process pipe with uniform interface
- [ ] Implement client: connection pooling, retries (idempotent methods only), timeouts, circuit breaker
- [ ] Implement server: concurrent request handling, worker-pool dispatch, backpressure (bounded queues)
- [ ] Implement RPC observability: method-level latency histograms, error rates, payload-size metrics

**Implementation Requirements & Constraints:**
- RPC must guarantee at-least-once delivery semantics with idempotency keys for mutations
- Timeouts must propagate end-to-end (deadline arithmetic across hops)

**Engineering Milestones (DoD):**
- [ ] RPC throughput ≥ 50k req/sec (in-process transport), ≥ 20k req/sec (TCP loopback); p99 latency < 5 ms
- [ ] Retry storm controlled by circuit breaker in 100% of failure-injection cases; zero non-idempotent retries

### 12.2 gRPC [x]
**Engineering Sub-tasks:**
- [ ] Implement gRPC integration: proto service definitions, codegen pipeline, server/client stubs
- [ ] Implement streaming RPC: server-stream (token streams), client-stream (batch upload), bidirectional
- [ ] Implement interceptors: auth, tracing, metrics, logging, rate-limiting (chain order defined)
- [ ] Implement keepalive/health: gRPC health protocol, keepalive pings, connection-drain on shutdown
- [ ] Implement gRPC observability: per-method stats, message-size tracking, flow-control window metrics

**Implementation Requirements & Constraints:**
- Proto files are the API contract: backward/forward compatible evolution rules (field numbers immutable)
- Flow control windows must be tuned for large-tensor streaming (≥ 16 MB window)

**Engineering Milestones (DoD):**
- [ ] All services expose health checks; streaming RPC delivers 100% of messages under 10k-message stress
- [ ] Interceptor chain adds ≤ 10% latency overhead; proto compatibility validated by breaking-change detector in CI

### 12.3 Worker Nodes [x]
**Engineering Sub-tasks:**
- [ ] Implement worker node agent: registration (heartbeat), capability advertisement (device, memory, dtype support)
- [ ] Implement task execution on worker: pull-model (work queue), task sandboxing, resource isolation (cgroup/memory limits)
- [ ] Implement worker lifecycle: join, drain (finish current tasks), leave, crash detection (heartbeat timeout)
- [ ] Implement worker load reporting: CPU/memory/GPU utilization, queue depth, current task load
- [ ] Implement worker security: mutual TLS, token auth, task-result integrity verification

**Implementation Requirements & Constraints:**
- Worker crash must not lose completed work: results acknowledged before task release
- Drain must complete within bounded time (configurable), then reject new tasks

**Engineering Milestones (DoD):**
- [ ] Heartbeat detection of dead workers < 2× heartbeat interval; zero task loss in worker-kill chaos test
- [ ] Worker throughput scales linearly to 16 workers on compute-bound workload; drain completes 100% of in-flight tasks

### 12.4 Cluster Manager [x]
**Engineering Sub-tasks:**
- [ ] Implement cluster manager: node registry, topology model (racks, NUMA nodes, link bandwidth)
- [ ] Implement placement engine: task-to-node assignment by resource fit, locality preference, anti-affinity
- [ ] Implement scaling: manual scale up/down, auto-scaling policies (CPU/memory/queue thresholds, cooldowns)
- [ ] Implement cluster state: consistent view (leader-elected or consensus), state persistence, snapshot/restore
- [ ] Implement cluster operations: rolling restart, drain, quarantine (unhealthy node isolation)

**Implementation Requirements & Constraints:**
- Cluster state must tolerate manager failover: persisted state + elected leader (Raft-lite or lease-based)
- Placement decisions must respect hard resource limits (never overcommit memory)

**Engineering Milestones (DoD):**
- [ ] Failover completes < 30 s with zero task re-execution (state restored); placement respects 100% of hard limits in 10k-task simulation
- [ ] Auto-scaling reacts within 2 policy intervals; rolling restart drops 0 tasks (drain-then-restart verified)

### 12.5 Parameter Server [x]
**Engineering Sub-tasks:**
- [ ] Implement parameter server: sharded parameter storage (key → tensor), pull/push API
- [ ] Implement update strategies: synchronous (barrier), asynchronous (stale-synchronous with staleness bound), hybrid
- [ ] Implement gradient aggregation: all-reduce fallback path, accumulation buffers, gradient compression (top-k sparsification, quantization)
- [ ] Implement consistency model: version counters per parameter, staleness-aware learning-rate correction
- [ ] Implement PS durability: periodic parameter checkpointing, replica replication (≥ 2 copies)

**Implementation Requirements & Constraints:**
- Async updates must bound staleness (τ) to preserve convergence (documented bound)
- Gradient compression must preserve convergence: error-feedback (residual accumulation) mandatory for top-k

**Engineering Milestones (DoD):**
- [ ] Synchronous PS matches single-machine training within 0.5% accuracy on 3 benchmarks; async with τ≤ 10 converges within 1%
- [ ] Gradient compression (top-1%) reduces traffic ≥ 10× with error-feedback converging within 1% of uncompressed

### 12.6 Distributed Scheduler [x]
**Engineering Sub-tasks:**
- [ ] Implement global scheduler: DAG partitioning (min-cut by communication cost), stage assignment to workers
- [ ] Implement pipelined execution: micro-batch pipeline schedule (GPipe/1F1B), bubble minimization
- [ ] Implement straggler mitigation: speculative execution (duplicate slow tasks), dynamic rebalancing
- [ ] Implement distributed barrier/collectives coordination: all-gather, reduce-scatter integration points
- [ ] Implement distributed scheduling policies: gang scheduling for all-to-all stages, elastic worker sets

**Implementation Requirements & Constraints:**
- Pipeline schedules must be deadlock-free (formal ordering of send/recv per stage)
- Partitioning must balance compute while minimizing cross-worker tensor transfers

**Engineering Milestones (DoD):**
- [ ] 1F1B schedule achieves bubble ratio ≤ 1/(num_stages) + ε on 4-stage benchmarks; speculative execution recovers ≥ 80% of straggler delay
- [ ] Distributed training matches single-node convergence on 3 benchmarks (within 0.5%); zero deadlocks in 1000 schedule simulations

### 12.7 Checkpoint Sync [x]
**Engineering Sub-tasks:**
- [ ] Implement distributed checkpoint coordination: global-step barriers, consistent-snapshot protocol (Chandy-Lamport-style)
- [ ] Implement sharded checkpoint aggregation: per-worker shards → consolidated checkpoint (parallel merge)
- [ ] Implement checkpoint replication: cross-node/cross-zone storage, quorum-write policy (W ≥ 2)
- [ ] Implement resume coordination: rank-aware restore (each worker loads its shard), global-step reconciliation
- [ ] Implement checkpoint consistency verification: cross-shard checksums, step-counter agreement

**Implementation Requirements & Constraints:**
- Distributed snapshots must be consistent: no torn state across workers at a barrier
- Restore must verify step agreement: mismatched steps trigger re-synchronization from last agreed step

**Engineering Milestones (DoD):**
- [ ] Failover recovery: training resumes from checkpoint with ≤ 1 checkpoint-interval of lost work in 100% of worker-kill tests
- [ ] Consistency verification catches 100% of injected torn-state cases; sharded restore ≥ 3× faster than centralized on 1B-param model

### 12.8 Fault Recovery [x]
**Engineering Sub-tasks:**
- [ ] Implement failure detection: heartbeat timeouts, health-probe classification (transient vs. permanent)
- [ ] Implement recovery strategies: task retry (bounded, exponential backoff), worker replacement, stage re-execution
- [ ] Implement checkpoint-based recovery: last-good-checkpoint restore, delta-replay of completed work
- [ ] Implement partial-failure handling: degrade (reduce batch/parallelism) vs. fail-over decisions
- [ ] Implement recovery audit: MTTR metrics, failure-class histogram, recovery-action log, post-mortem data capture

**Implementation Requirements & Constraints:**
- Recovery must be exactly-once for stateful stages (idempotent replay with dedup keys)
- Cascading failure prevention: recovery actions rate-limited, backoff-jittered

**Engineering Milestones (DoD):**
- [ ] MTTR < 60 s for single-worker failure on reference cluster; exactly-once verified in 100% of replay tests
- [ ] Zero cascading failures in chaos-engine suite (100 injected faults); all recovery actions logged and rate-limited

---

## PHASE 13 — PLUGIN SDK (7 modules)

### 13.1 Plugin API [x]
**Engineering Sub-tasks:**
- [ ] Define plugin API surface: stable interface set (`Init`, `Execute`, `Shutdown`, `Capabilities`), versioned API contracts
- [ ] Implement plugin context: engine handle, logger, config access, resource limits, cancellation token
- [ ] Implement typed plugin categories: op-plugin, optimizer-plugin, backend-plugin, data-plugin, hook-plugin
- [ ] Implement API versioning: semantic API versions, deprecated-marker registry, migration guides per version
- [ ] Implement plugin API tests: conformance suite (mock engine) for each plugin category

**Implementation Requirements & Constraints:**
- Plugin API is frozen per MAJOR version: no removal, only additions/deprecations
- Plugins must not access engine internals: all interaction through API surface (enforced by package boundaries)

**Engineering Milestones (DoD):**
- [ ] Conformance suite passes for 100% of shipped reference plugins; API stability verified by compatibility harness (old plugins run on new engine within MAJOR)
- [ ] Plugin API documentation covers 100% of exported symbols with examples

### 13.2 Loader [x]
**Engineering Sub-tasks:**
- [ ] Implement plugin discovery: plugin directory scan, manifest (plugin.json) parsing, validation
- [ ] Implement plugin loading: dynamic library load (plugin/so), symbol resolution (`astrovox_plugin_*`), entry invocation
- [ ] Implement dependency resolution: plugin-declared dependencies, version constraints, load-order topological sort
- [ ] Implement sandbox isolation: plugin process isolation (future), resource caps, syscall filtering hooks
- [ ] Implement loader lifecycle: load → init → ready, with per-phase error handling and unload/cleanup

**Implementation Requirements & Constraints:**
- Plugins loaded in dependency order; cyclic dependencies rejected with cycle report
- Failed plugin load must not crash host: errors isolated, remaining plugins unaffected

**Engineering Milestones (DoD):**
- [ ] Loader handles 100 plugins in < 5 s; cyclic dependency detection 100% accurate on 1000-graph suite
- [ ] Fault isolation: crashing plugin fails only itself (process-isolation mode) in 100% of crash-injection tests

### 13.3 Sandbox [x]
**Engineering Sub-tasks:**
- [ ] Implement sandbox policy: syscall allowlist (seccomp-bpf profile), filesystem jail (read-only mounts), network egress control
- [ ] Implement resource limits: CPU quota, memory cap, execution timeout per plugin invocation
- [ ] Implement capability gating: plugin requests capabilities, policy grants/denies per deployment profile
- [ ] Implement audit logging: syscall violations, resource-limit hits, capability denials with context
- [ ] Implement sandbox escape detection: integrity checks on host symbols, canary tokens

**Implementation Requirements & Constraints:**
- Default-deny policy: all capabilities denied unless explicitly granted in profile
- Sandbox violations fail the plugin invocation, never the host

**Engineering Milestones (DoD):**
- [ ] Syscall allowlist blocks 100% of forbidden syscalls in escape-attempt suite (50 cases); resource caps enforced (100% of over-limit invocations terminated)
- [ ] Zero host-process impact from sandboxed plugin crashes; audit log captures 100% of violations

### 13.4 Capability System [x]
**Engineering Sub-tasks:**
- [ ] Implement capability model: typed capabilities (`Compute.GPU`, `Network.Egress`, `FileSystem.Write`, `Secret.Read`)
- [ ] Implement capability issuance: signed capability tokens (HMAC), expiry, delegation rules
- [ ] Implement capability enforcement: middleware checks at API boundaries, deny-by-default
- [ ] Implement capability auditing: issuance/use/revocation events with principal context
- [ ] Implement capability introspection: `Capabilities()` query per plugin, policy preview tool

**Implementation Requirements & Constraints:**
- Capabilities are least-privilege: plugins receive exactly declared set, no implicit grants
- Capability tokens expire ≤ 24 h default; revocation is immediate (check-before-use)

**Engineering Milestones (DoD):**
- [ ] Enforcement denies 100% of undeclared capability uses in adversarial suite; tokens forge-resistant (HMAC verification test with known key)
- [ ] Audit trail complete: 100% of capability events logged with principal + timestamp; policy preview matches enforcement behavior

### 13.5 Version Compatibility [x]
**Engineering Sub-tasks:**
- [ ] Implement compatibility matrix: plugin API version ↔ engine version ranges, per-plugin min/max
- [ ] Implement compatibility checks at load: semantic-version constraint evaluation, deprecation warnings
- [ ] Implement adapter layer: shim old plugin API versions onto current API where feasible
- [ ] Implement compatibility testing harness: run plugin against multiple engine versions (matrix CI job)
- [ ] Implement version-reporting: plugin declares API version, engine reports supported range

**Implementation Requirements & Constraints:**
- MAJOR version mismatch = hard rejection; MINOR/PATCH mismatches = warning or adapter
- Adapters must be behavior-preserving (equivalence tests per adapter)

**Engineering Milestones (DoD):**
- [ ] Compatibility gate rejects 100% of MAJOR mismatches; adapters preserve behavior on 100% of legacy-plugin corpus
- [ ] Matrix CI runs 100% of reference plugins across 3 engine versions; compatibility report generated per run

### 13.6 Dependency Manager [x]
**Engineering Sub-tasks:**
- [ ] Implement dependency declaration: manifest format (name, version-range, checksum), lockfile generation
- [ ] Implement dependency resolution: SAT-style resolver for version constraints, conflict reporting
- [ ] Implement dependency fetching: content-addressed store, checksum verification, offline cache
- [ ] Implement dependency isolation: per-plugin dependency namespaces (no cross-plugin symbol leakage)
- [ ] Implement dependency auditing: known-vulnerability scan (advisory DB), license compliance report

**Implementation Requirements & Constraints:**
- Dependency resolution must be deterministic: lockfile pins exact versions and checksums
- Unverified checksums are hard failures (supply-chain protection)

**Engineering Milestones (DoD):**
- [ ] Resolver solves 1000-constraint instances < 10 s; conflicts reported with minimal unsatisfiable core
- [ ] Zero unverified dependencies loaded (checksum enforcement test); vulnerability scan covers 100% of resolved deps against advisory DB

### 13.7 Marketplace Format [x]
**Engineering Sub-tasks:**
- [ ] Define marketplace package format: archive layout (manifest, binary, docs, signatures, checksums)
- [ ] Implement package signing/verification: Ed25519 signatures, publisher key registry, signature chain
- [ ] Implement package index: catalog metadata (name, version, category, ratings), search/filter API
- [ ] Implement package install/uninstall: transactional install (all-or-nothing), rollback on failure
- [ ] Implement marketplace CI: automated conformance + sandbox tests before package acceptance

**Implementation Requirements & Constraints:**
- Packages must be signed by registered publishers; unsigned packages rejected by default
- Install is transactional: failure rolls back completely (no partial state)

**Engineering Milestones (DoD):**
- [ ] Signature verification rejects 100% of tampered packages (mutation suite); install rollback leaves zero residue in 100% of failure injections
- [ ] Package index search p95 < 100 ms at 10k packages; conformance CI blocks 100% of non-conforming packages

---

## PHASE 14 — CLI (10 modules)

### 14.1 astrovox init [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox init`: project scaffolding (config, dirs, .gitignore, license templates)
- [ ] Implement interactive wizard: project name, language target, backend selection, defaults confirmation
- [ ] Implement templates: minimal / standard / distributed project layouts with sample config
- [ ] Implement idempotency: re-init updates missing files only, preserves local modifications (diff report)
- [ ] Implement validation: post-init dry-run (`astrovox doctor` hook) verifying environment readiness

**Implementation Requirements & Constraints:**
- Init must never overwrite user files without confirmation (`--force` explicit)
- Templates are versioned; template migration path for newer versions

**Engineering Milestones (DoD):**
- [ ] Init completes < 2 s; scaffolds buildable project verified by `build` on all 3 templates
- [ ] Re-init preserves 100% of user modifications (file-hash test); wizard accessible non-interactively via flags

### 14.2 astrovox build [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox build`: graph compilation from source/config, target backend selection, artifact output
- [ ] Implement build profiles: debug/release, cross-compilation targets, optimization level flags
- [ ] Implement build cache: content-hash keyed, incremental rebuild of changed subgraphs
- [ ] Implement build diagnostics: error/warning formatting with source spans, error codes, machine-readable output (JSON)
- [ ] Implement build report: artifact manifest (size, checksum, ops, backend), build time breakdown

**Implementation Requirements & Constraints:**
- Build cache must be correct: any input change (code/config/data) invalidates dependent artifacts
- Build output must be deterministic: same inputs → identical artifact bytes

**Engineering Milestones (DoD):**
- [ ] Incremental rebuild ≥ 5× faster than clean on single-op change; determinism verified by byte-comparison of two builds
- [ ] Build succeeds for all example models (50-model corpus); diagnostics accurate on 100% of seeded errors

### 14.3 astrovox train [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox train`: training-loop driver (dataset → model → loss → optimizer → checkpoint)
- [ ] Implement training flags: epochs, batch size, lr schedule, precision, seed, distributed config
- [ ] Implement progress reporting: epoch/step, loss curves (EMA), throughput (samples/sec), ETA
- [ ] Implement checkpointing integration: schedule-based, metric-based (best), on-signal (SIGUSR1)
- [ ] Implement training resume: automatic resume from latest checkpoint with config-diff warning

**Implementation Requirements & Constraints:**
- Training must be resumable: any interruption resumes with identical trajectory (RNG/optimizer state)
- Config for training must be validated pre-run (shape checks, resource pre-flight)

**Engineering Milestones (DoD):**
- [ ] Resume-after-kill reproduces identical loss curve (bit-exact) on 50 runs; training throughput within 5% of API-equivalent loop
- [ ] Progress output non-blocking (p99 < 1% overhead); checkpoint-on-signal tested with SIGKILL chaos (≤ 1 interval loss)

### 14.4 astrovox infer [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox infer`: single/batch inference from model + input (file/stdin/API source)
- [ ] Implement generation controls: max tokens, temperature, top-k, top-p, stop sequences, seed
- [ ] Implement output modes: raw text, JSON (tokens+logprobs), streaming (line-delimited)
- [ ] Implement model loading optimization: lazy device placement, weight quantization on load
- [ ] Implement inference diagnostics: TTFT, tokens/sec, memory footprint, attention-pattern export (debug)

**Implementation Requirements & Constraints:**
- Inference must be deterministic with fixed seed (same prompt → same output)
- Memory pre-flight: reject requests exceeding available device memory before generation

**Engineering Milestones (DoD):**
- [ ] Determinism verified on 100 prompts × 3 runs (identical output); throughput ≥ 80% of API-equivalent
- [ ] Streaming mode emits first token < 500 ms p95 on reference model; JSON/logprob output validated against schema

### 14.5 astrovox profile [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox profile`: instrumented execution with CPU/memory/kernel profiling
- [ ] Implement profile views: op table (time/self/memory), flamegraph export, memory timeline
- [ ] Implement comparison mode: baseline vs. candidate profile diff (per-op deltas, regression flags)
- [ ] Implement hardware counters (where available): cache misses, branch misses, IPC
- [ ] Implement profile export: JSON, pprof, Chrome trace, markdown report

**Implementation Requirements & Constraints:**
- Profiling must not alter program semantics (same outputs, documented overhead)
- Overhead must be quantified and reported in the profile output itself

**Engineering Milestones (DoD):**
- [ ] Profile overhead ≤ 10% (measured, reported); op-time attribution within 5% of manual instrumentation
- [ ] Regression detection flags ≥ 95% of injected regressions (20 cases) with correct op attribution

### 14.6 astrovox benchmark [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox benchmark`: micro/macro benchmark runner with fixed workloads
- [ ] Implement benchmark suite: op-level (Phase 0.9 harness), model-level (reference models), system-level (end-to-end)
- [ ] Implement statistics engine: mean/p50/p95/p99, stdev, CoV, confidence intervals, outlier handling
- [ ] Implement comparison: baseline-file diff with regression thresholds, machine-readable results
- [ ] Implement benchmark persistence: results DB (SQLite), trend queries, CI artifact export

**Implementation Requirements & Constraints:**
- Benchmarks must be reproducible: fixed seeds, warmup, CPU pinning, environment capture
- Statistical rigor: minimum sample size for CI claims (power analysis), outlier policy documented

**Engineering Milestones (DoD):**
- [ ] CoV < 3% across 10 runs on stable hardware; regression detection (5% threshold) with p < 0.01 on 100 cases
- [ ] Full benchmark suite completes < 15 min; results DB supports 1-year trend queries < 1 s

### 14.7 astrovox graph [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox graph`: IR/graph inspection from build artifact or live session
- [ ] Implement graph output: DOT/GraphViz, JSON (viewer format), text summary (ops, params, memory)
- [ ] Implement graph analysis: critical path, memory estimate, op histogram, dtype distribution
- [ ] Implement graph diff: two-graph structural comparison (added/removed/changed nodes)
- [ ] Implement graph validation hook: run `ValidateGraph` with report formatting

**Implementation Requirements & Constraints:**
- Graph output must handle 100k-node graphs (streaming, pagination) without OOM
- Diff must be structural (not textual): node identity by (op, attributes, inputs)

**Engineering Milestones (DoD):**
- [ ] Graph export of 10k-node model < 5 s; analysis (critical path, memory) < 1 s
- [ ] Diff correctly identifies 100% of injected graph changes (100 cases); validation report matches API output

### 14.8 astrovox doctor [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox doctor`: environment diagnostic suite (CPU features, memory, disk, GPU, network, deps)
- [ ] Implement check catalog: ≥ 30 checks (BLAS availability, SIMD support, config validity, plugin health, version skew)
- [ ] Implement severity classification: info/warn/error with remediation guidance per finding
- [ ] Implement machine-readable output: JSON report for automation/CI gating
- [ ] Implement performance sanity: quick benchmark (10 s cap) to detect degraded environments

**Implementation Requirements & Constraints:**
- Doctor must be read-only: no system mutation (except optional `--fix` for known-safe items)
- Checks must complete < 30 s total; each check individually timeout-bounded

**Engineering Milestones (DoD):**
- [ ] Doctor detects 100% of injected environment faults (20 cases: missing BLAS, low memory, bad config); false-positive rate < 2% on healthy hosts
- [ ] JSON report schema-stable (validated); `--fix` resolves ≥ 80% of fixable findings

### 14.9 astrovox plugin [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox plugin`: list, install, uninstall, update, info, enable/disable subcommands
- [ ] Implement plugin discovery query: installed/available, version, compatibility status
- [ ] Implement plugin lifecycle ops: load/unload without restart, dependency display, conflict report
- [ ] Implement plugin dev workflow: `plugin create` scaffold, `plugin test` (conformance), `plugin package` (marketplace format)
- [ ] Implement plugin sandbox controls: capability grant/revoke, resource-limit overrides per plugin

**Implementation Requirements & Constraints:**
- Plugin commands are transactional: failed install/uninstall leaves consistent state
- Enable/disable requires no engine restart (hot-swap path)

**Engineering Milestones (DoD):**
- [ ] Install/uninstall round-trip: 100% clean state (no residue) in 100 cases; hot-swap verified with 0 downtime in live-session test
- [ ] `plugin test` catches 100% of non-conforming plugins (conformance suite); packaging produces valid marketplace archives

### 14.10 astrovox docs [x]
**Engineering Sub-tasks:**
- [ ] Implement `astrovox docs`: doc generation (API reference, CLI docs, config docs) and serving (local preview)
- [ ] Implement doc sources: code comments (godoc/pdoc), config schema (JSON Schema → docs), examples corpus
- [ ] Implement doc search: full-text index over generated docs, ranked search API
- [ ] Implement doc validation: link checking, example execution, API-coverage report (undocumented symbols)
- [ ] Implement doc export: HTML, Markdown, PDF (via LaTeX), single-page formats

**Implementation Requirements & Constraints:**
- Generated docs must be deterministic (byte-identical across runs)
- Examples in docs are executable tests (doc-as-code guarantee)

**Engineering Milestones (DoD):**
- [ ] Doc generation < 2 min for full repo; link-check finds 0 broken links on generated output
- [ ] API coverage ≥ 98% of exported symbols; example execution passes 100% in clean environment

---

## PHASE 15 — DEVELOPER TOOLS (8 modules)

### 15.1 Formatter [x]
**Engineering Sub-tasks:**
- [ ] Implement ASTROVOX language formatter: lexer → AST → canonical pretty-print with configurable style
- [ ] Implement style rules: indentation (2/4/space/tab), line width (80/100/120), operator wrapping, import grouping
- [ ] Implement idempotency: format(format(x)) == format(x) for all inputs
- [ ] Implement safety: formatter never changes semantics (AST-equivalence check pre/post)
- [ ] Implement integration: `--check` mode (CI), `--write`, editor LSP support, range-formatting

**Implementation Requirements & Constraints:**
- Formatter must preserve all comments and source spans (round-trip trivia)
- Formatting must be deterministic: same input + config → identical output

**Engineering Milestones (DoD):**
- [ ] Idempotency holds on 10k corpus; semantic equivalence verified on 100% of formatted files (AST-diff)
- [ ] Format throughput ≥ 10k LOC/s; `--check` exit-code correctness on 100% of CI cases

### 15.2 Linter [x]
**Engineering Sub-tasks:**
- [ ] Implement lint rule engine: AST/pattern-based rules with severity, autofix capability, rule documentation
- [ ] Implement rule catalog (≥ 40 rules): unused vars, shadowing, magic numbers, perf anti-patterns (in-place hazards), API misuse
- [ ] Implement autofix: safe fixes only (mechanical, verified by AST-equivalence), fix-count limits per run
- [ ] Implement rule configuration: per-rule enable/disable/severity, path-scoped overrides, preset profiles
- [ ] Implement lint reporting: sorted diagnostics (file/line/rule), summary counts, SARIF export (CI integration)

**Implementation Requirements & Constraints:**
- Autofix must be semantics-preserving (AST-equivalence verified); unsafe rules report-only
- Lint must be fast: < 1 s per 10k LOC (parallel file processing)

**Engineering Milestones (DoD):**
- [ ] Rules detect 100% of seeded violations (40 rule × 10 cases); autofix correct on 100% of fixable cases (equivalence-verified)
- [ ] Zero false positives on clean corpus; SARIF export loads in GitHub code-scanning format

### 15.3 Profiler [x]
**Engineering Sub-tasks:**
- [ ] Implement profiler tool: CPU (sampling), memory (allocation), GPU-kernel (event-based), I/O profiling modes
- [ ] Implement analysis views: hot paths, call trees, flamegraphs, memory leak suspects, kernel latency tables
- [ ] Implement comparison workflows: A/B profiles, regression detection, per-change deltas
- [ ] Implement remote profiling: attach to running session (auth + TLS), live-streaming samples
- [ ] Implement profiler export: pprof, Speedscope, JSON, markdown summary

**Implementation Requirements & Constraints:**
- Profiler must not require code changes (zero-instrumentation for CPU/memory modes)
- Remote profiling is read-only: no mutation of target state

**Engineering Milestones (DoD):**
- [ ] CPU attribution error ≤ 5% vs. instrumented baseline; memory profiling identifies 100% of injected leaks
- [ ] Remote profiling overhead ≤ 3%; A/B comparison detects ≥ 90% of perf regressions (15-case suite)

### 15.4 Debugger [x]
**Engineering Sub-tasks:**
- [ ] Implement debugger tool: attach/listen modes, breakpoints (file:line, op-id, function), conditional breakpoints
- [ ] Implement stepping: step-into/over/out, continue, restart-from-checkpoint
- [ ] Implement inspection: variable/tensor watch (values, shapes, dtypes, stats), call-stack view, graph state
- [ ] Implement expression evaluation: sandboxed REPL in paused context (read-only by default)
- [ ] Implement debugger UI integration: TUI (terminal) + LSP/DAP protocol for IDEs

**Implementation Requirements & Constraints:**
- Debugger must support deterministic replay: same seed → same execution path
- Expression evaluation is sandboxed: no side effects unless explicitly enabled

**Engineering Milestones (DoD):**
- [ ] Breakpoints/stepping correct on 100% of 200 test programs; watch values match actual state in 100% of samples
- [ ] DAP protocol passes IDE integration tests (VS Code harness); replay determinism verified on 100 cases

### 15.5 Graph Viewer [x]
**Engineering Sub-tasks:**
- [ ] Implement interactive graph viewer: pan/zoom, node search, filter by op-type/device/time
- [ ] Implement node detail panel: attributes, input/output shapes, dtype, profiling data (time/memory)
- [ ] Implement layout modes: layered (topological), force-directed, grouped by scope/subgraph
- [ ] Implement large-graph handling: virtualization (render visible only), LOD (collapse subgraphs), 100k-node support
- [ ] Implement session features: saved layouts, annotations, diff-overlay mode (two graphs)

**Implementation Requirements & Constraints:**
- Viewer must render ≥ 30 fps with 10k visible nodes (GPU-accelerated canvas/WebGL)
- Node data loads progressively: metadata-first, details-on-demand

**Engineering Milestones (DoD):**
- [ ] 10k-node graph interactive at 30 fps (mid-range hardware); search < 100 ms at 100k nodes
- [ ] Profiling overlay matches profiler data (1% tolerance); diff-overlay correctly highlights 100% of structural changes

### 15.6 IR Viewer [x]
**Engineering Sub-tasks:**
- [ ] Implement IR viewer: HIR/MIR/SSA/Graph-IR visualization with stage selector
- [ ] Implement pass-through view: IR state before/after each optimization pass, side-by-side diff
- [ ] Implement SSA-specific views: dominance tree overlay, phi-node highlighting, value-number coloring
- [ ] Implement instruction-level view: MIR listing with operands, liveness ranges, slot assignment
- [ ] Implement IR search: by value name, op type, span (source location), type/dtype

**Implementation Requirements & Constraints:**
- IR viewer consumes pipeline dumps (Phase 6.10) without regeneration
- Source-span links navigate to original source (editor integration)

**Engineering Milestones (DoD):**
- [ ] All IR stages render for 100% of pipeline-dump corpus; diff view identifies 100% of pass-induced changes
- [ ] SSA views correct (dominance tree matches computed tree) on 100 functions; search p95 < 200 ms at 50k instructions

### 15.7 Memory Visualizer [x]
**Engineering Sub-tasks:**
- [ ] Implement memory visualizer: heap timeline (RSS/heap/pool bytes), allocation-size histogram, lifetime heatmap
- [ ] Implement allocator views: arena/slab/buddy/pool utilization, fragmentation index over time
- [ ] Implement buffer-flow diagram: allocation sites → tensors → release sites (Sankey)
- [ ] Implement leak spotlight: unreleased allocations ranked by bytes/age with stack traces
- [ ] Implement snapshot comparison: two-time snapshots → delta analysis (growth/leak suspects)

**Implementation Requirements & Constraints:**
- Visualizer data comes from memory profiler (Phase 2.9) with bounded memory overhead
- Stack traces symbolized offline (deferred to avoid hot-path cost)

**Engineering Milestones (DoD):**
- [ ] Visualizer correctly attributes ≥ 95% of bytes to allocation sites; leak spotlight finds 100% of injected leaks
- [ ] Timeline renders 1-hour capture at 60 fps (downsampling); fragmentation index matches ground truth within 5%

### 15.8 Benchmark Dashboard [x]
**Engineering Sub-tasks:**
- [ ] Implement benchmark dashboard: real-time results view (latency, throughput, memory), per-benchmark drill-down
- [ ] Implement trend analysis: historical charts, regression alerts, environment-correlated anomalies
- [ ] Implement comparison views: branches/commits/versions side-by-side, statistical significance display
- [ ] Implement reporting: scheduled reports (daily/weekly), alert integration (Phase 19), artifact links
- [ ] Implement dashboard API: REST/GraphQL query layer with pagination and caching

**Implementation Requirements & Constraints:**
- Dashboard queries must be sub-second on 1-year result DB (indexed, pre-aggregated)
- Statistical claims require confidence intervals (no bare averages)

**Engineering Milestones (DoD):**
- [ ] Dashboard p95 query latency < 500 ms at 1M stored results; regression alerts fire within 5 min of CI completion
- [ ] Trend charts match raw-data recomputation exactly (pre-aggregation verified); alert false-positive rate < 5%

---

## PHASE 16 — SECURITY (7 modules)

### 16.1 JWT [x]
**Engineering Sub-tasks:**
- [ ] Implement JWT issuance: HS256/RS256/EdDSA signing, claims set (sub, iss, aud, exp, iat, jti), token-id registry
- [ ] Implement JWT validation: signature verification, expiry/issuer/audience checks, revocation-list lookup
- [ ] Implement refresh-token flow: rotating refresh tokens, reuse detection (family invalidation), secure storage flags
- [ ] Implement token security: algorithm pinning (no `alg:none`), key rotation with overlap window, kid header routing
- [ ] Implement JWT observability: issuance/validation metrics, failure-reason histogram, token-replay detection

**Implementation Requirements & Constraints:**
- Default algorithm EdDSA/RS256; HS256 only for legacy with explicit config
- Token lifetimes ≤ 15 min (access), revocation check on sensitive operations

**Engineering Milestones (DoD):**
- [ ] Validation rejects 100% of forged/tampered/expired tokens (200-case suite); replay detection catches 100% of jti-reuse cases
- [ ] Key rotation: zero validation failures during overlap window; throughput ≥ 20k validations/sec

### 16.2 OAuth [x]
**Engineering Sub-tasks:**
- [ ] Implement OAuth 2.0/OIDC: authorization-code flow with PKCE, token endpoint, userinfo endpoint
- [ ] Implement provider integration: discovery (`.well-known`), JWKS fetch with caching/rotation, scopes mapping
- [ ] Implement state/nonce management: CSRF state token, nonce binding to ID-token validation
- [ ] Implement token storage: encrypted session store, token-refresh scheduler, logout revocation
- [ ] Implement OAuth security: redirect-URI exact matching, state entropy (≥ 128 bits), PKCE enforcement

**Implementation Requirements & Constraints:**
- PKCE mandatory for all clients (public + confidential); implicit flow disabled
- JWKS caching respects key expiry; key-rotation handled without downtime

**Engineering Milestones (DoD):**
- [ ] Flow passes OIDC conformance suite (RP tests); CSRF/state-attack suite blocked 100% (50 cases)
- [ ] Token refresh succeeds across JWKS rotation in 100% of rotation tests; login p95 < 800 ms (excluding IdP latency)

### 16.3 RBAC [x]
**Engineering Sub-tasks:**
- [ ] Implement RBAC model: users → roles → permissions (resource:action), hierarchy (role inheritance), constraints (SoD)
- [ ] Implement policy evaluation: deny-by-default, explicit-deny override, permission resolution with inheritance expansion
- [ ] Implement enforcement middleware: route/operation guards, resource-level checks (ABAC extensions for owners)
- [ ] Implement RBAC management: role CRUD, audit trail of assignments, bulk-import with validation
- [ ] Implement RBAC testing: permission-matrix tests, privilege-escalation attack suite

**Implementation Requirements & Constraints:**
- Policy evaluation is O(roles + inherited-perms) with memoization; no unbounded inheritance chains (depth ≤ 5)
- All authorization decisions are logged (who/what/when/result)

**Engineering Milestones (DoD):**
- [ ] Enforcement denies 100% of unauthorized accesses in privilege-escalation suite (100 cases); policy evaluation p99 < 100 µs
- [ ] Permission matrix tests cover 100% of role-permission combinations; audit trail lossless under load

### 16.4 Encryption [x]
**Engineering Sub-tasks:**
- [ ] Implement crypto primitives wrapper: AES-256-GCM, ChaCha20-Poly1305, HKDF, SHA-256/512, Argon2id
- [ ] Implement envelope encryption: data keys per object, KEK rotation, key-version tracking in ciphertext header
- [ ] Implement at-rest encryption: tensor/checkpoint/config encryption with AEAD, integrity verification on load
- [ ] Implement in-transit TLS: TLS 1.3 only, certificate pinning option, cipher-suite policy
- [ ] Implement crypto hygiene: constant-time comparisons, secure memory zeroing, RNG from system CSPRNG

**Implementation Requirements & Constraints:**
- No custom crypto: primitives only from vetted libraries (Go crypto, ring)
- Key material never logged; zeroing on release for sensitive buffers

**Engineering Milestones (DoD):**
- [ ] AEAD round-trip correct on 10k cases; tampered ciphertext rejected 100% (integrity test); envelope rotation preserves access to old versions
- [ ] TLS config passes sslyze grade A; crypto wrappers constant-time verified (timing test, no data-dependent branches)

### 16.5 Secret Manager [x]
**Engineering Sub-tasks:**
- [ ] Implement secret manager: store/retrieve/rotate secrets with versioned values (K/V + metadata)
- [ ] Implement backend adapters: file (dev), Vault, cloud KMS (AWS/GCP/Azure) via provider interface
- [ ] Implement access control: per-secret ACL, lease/TTL-based dynamic secrets, audit logging
- [ ] Implement secret injection: runtime resolution into config (no plaintext on disk), in-memory only
- [ ] Implement rotation automation: scheduled rotation, dual-active window, consumer reload notification

**Implementation Requirements & Constraints:**
- Secrets never appear in logs, config dumps, error messages (redaction filter mandatory)
- Secret reads are audited with caller identity; caching respects TTL (no stale secrets)

**Engineering Milestones (DoD):**
- [ ] Zero secret leakage in 10k-log redaction test; rotation completes with zero downtime (dual-window verified)
- [ ] Access denial for 100% of unauthorized callers (ACL suite); audit log captures 100% of secret reads

### 16.6 Audit Logs [x]
**Engineering Sub-tasks:**
- [ ] Implement audit log schema: event (who, what, when, where, result), immutable append-only store
- [ ] Implement event capture: auth events, config changes, data access (sensitive), admin operations, plugin actions
- [ ] Implement log integrity: hash-chaining (Merkle-style), tamper evidence, signed log segments
- [ ] Implement retention/compliance: configurable retention, export (JSON/CSV), GDPR redaction hooks
- [ ] Implement audit query: time-range, principal, action-type filters with pagination

**Implementation Requirements & Constraints:**
- Audit writes are non-blocking (async sink) and loss-bounded (disk-backed queue)
- Audit logs are append-only: no update/delete path (integrity by construction)

**Engineering Milestones (DoD):**
- [ ] Tamper detection catches 100% of log mutations (chain-verify test); ingestion ≥ 50k events/sec
- [ ] Audit trail completeness: 100% of captured event types present under load; query p95 < 500 ms at 100M events

### 16.7 API Security [x]
**Engineering Sub-tasks:**
- [ ] Implement API security middleware: auth (JWT/OAuth), rate limiting (token bucket per principal), input validation
- [ ] Implement request hardening: size limits, timeout enforcement, header sanitization, CORS policy
- [ ] Implement abuse protection: brute-force detection (exponential backoff), anomaly scoring, IP reputation hooks
- [ ] Implement API threat defenses: injection prevention (parameterized everything), SSRF guards (egress allowlist)
- [ ] Implement security headers: HSTS, CSP, X-Content-Type-Options, CORS preflight handling

**Implementation Requirements & Constraints:**
- All user input validated against schemas before processing (no trust boundaries crossed unvalidated)
- Rate limits are per-principal and per-endpoint with burst allowance

**Engineering Milestones (DoD):**
- [ ] Rate limiter enforces limits within 1% under 10k-req burst; auth middleware rejects 100% of unauthenticated calls
- [ ] Security headers present on 100% of responses; SSRF guard blocks 100% of private-IP attempts (suite); OWASP Top-10 test suite passes

---

## PHASE 17 — NETWORKING (7 modules)

### 17.1 HTTP [x]
**Engineering Sub-tasks:**
- [ ] Implement HTTP/1.1 server: request parsing, keep-alive, chunked transfer, content negotiation
- [ ] Implement HTTP/1.1 client: connection pooling, redirect policy, cookie jar, retry idempotency
- [ ] Implement routing: method+path matching (radix tree), middleware chain, URL parameter extraction
- [ ] Implement request/response lifecycle: headers, body streaming, trailers, compression (gzip/br)
- [ ] Implement HTTP observability: per-route metrics (latency, status, size), access logging

**Implementation Requirements & Constraints:**
- Server must handle 10k concurrent connections (epoll-backed); no per-connection thread
- Request body must be size-limited and streamed (no unbounded buffering)

**Engineering Milestones (DoD):**
- [ ] Throughput ≥ 50k req/sec (loopback, 256B responses); keep-alive reuse rate ≥ 90%
- [ ] Routing p99 < 50 µs at 10k routes; 100% of malformed requests rejected without connection loss

### 17.2 HTTP/2 [x]
**Engineering Sub-tasks:**
- [ ] Implement HTTP/2 framing: frame parser/builder (HEADERS, DATA, SETTINGS, PING, GOAWAY)
- [ ] Implement stream multiplexing: stream state machine, flow control (per-stream + connection windows)
- [ ] Implement HPACK: header compression (static/dynamic tables, Huffman coding)
- [ ] Implement server push (optional, disable-by-default), priority/dependency tree
- [ ] Implement TLS ALPN negotiation (h2) and prior-knowledge (cleartext upgrade) paths

**Implementation Requirements & Constraints:**
- Flow-control windows must be enforced: no sender overrun (window exhaustion blocks)
- SETTINGS frames validated; peer misbehavior triggers GOAWAY with error code

**Engineering Milestones (DoD):**
- [ ] HTTP/2 conformance: passes h2spec test suite; multiplexed streams deliver in-order per stream
- [ ] HPACK compression ≥ 80% header reduction; 100 concurrent streams with zero inter-stream head-of-line blocking beyond TCP

### 17.3 HTTP/3
**Engineering Sub-tasks:**
- [ ] Implement HTTP/3 mapping: QUIC streams → request/response, QPACK header compression
- [ ] Implement QPACK: static table, dynamic table with insert-count tracking, decoder stream
- [ ] Implement connection migration: connection-ID routing, path validation, 0-RTT resumption (configurable)
- [ ] Implement HTTP/3 server: alt-svc advertisement, graceful fallback to HTTP/2
- [ ] Implement HTTP/3 observability: per-stream metrics, QUIC loss/retransmit stats correlation

**Implementation Requirements & Constraints:**
- HTTP/3 requires UDP; UDP receive buffers sized for 10k+ concurrent flows
- 0-RTT data is replay-risk: only idempotent methods allowed (GET)

**Engineering Milestones (DoD):**
- [ ] HTTP/3 passes quic-interop/minimal conformance; connection migration preserves streams (100% of test handoffs)
- [ ] QPACK matches header-compression ratio of HPACK within 5%; 0-RTT only for GET (100% enforced)

### 17.4 TCP [x]
**Engineering Sub-tasks:**
- [ ] Implement TCP transport layer: socket management, non-blocking I/O, keepalive, Nagle policy
- [ ] Implement connection lifecycle: dial (with timeout), handshake, idle timeout, graceful close (FIN sequencing)
- [ ] Implement message framing: length-prefix codec, delimiter codec, max-frame-size enforcement
- [ ] Implement TCP tuning: buffer sizes (SO_RCVBUF/SO_SNDBUF), TCP_NODELAY, congestion-control selection
- [ ] Implement TCP resilience: reconnect with backoff+jitter, split-brain detection (heartbeat)

**Implementation Requirements & Constraints:**
- Framing codec must be streaming (partial-frame tolerant); frame size capped (default 16 MB)
- Keepalive detects dead peers within 2× keepalive interval

**Engineering Milestones (DoD):**
- [ ] Framing codec handles 10M messages with 0 framing errors (chunked-feeding test); reconnect succeeds in 100% of drop-recover cases
- [ ] Throughput ≥ 5 GB/s loopback (1MB messages); dead-peer detection < 15 s with default keepalive

### 17.5 UDP [x]
**Engineering Sub-tasks:**
- [ ] Implement UDP transport: socket setup, receive batching (recvmmsg), send batching (sendmmsg)
- [ ] Implement reliability layer (optional): ACK/NACK, selective repeat, retransmission timer
- [ ] Implement congestion control: LEDBAT/TFRC-style rate control for custom UDP protocols
- [ ] Implement multicast/broadcast: group join/leave, loopback control, TTL policy
- [ ] Implement UDP observability: loss rate, out-of-order rate, jitter histogram

**Implementation Requirements & Constraints:**
- UDP datagrams size-capped by MTU (fragmentation avoided; 1200B safe default)
- Reliability layer must be idempotent: duplicate datagrams deduplicated by sequence number

**Engineering Milestones (DoD):**
- [ ] Receive batching ≥ 1M datagrams/sec; loss-recovery delivers 100% of packets in 5% loss environment (reliability mode)
- [ ] Congestion control converges within 3 RTTs (rate stabilizes); multicast delivery verified on multi-host test bed

### 17.6 WebSocket [x]
**Engineering Sub-tasks:**
- [ ] Implement WebSocket handshake: HTTP Upgrade, Sec-WebSocket-Accept computation, subprotocol negotiation
- [ ] Implement frame codec: text/binary/ping/pong/close, masking (client→server), fragmentation
- [ ] Implement connection management: heartbeat (ping interval), close handshake (status codes), backpressure
- [ ] Implement message handling: per-message compression (permessage-deflate), size limits
- [ ] Implement WebSocket observability: message rates, latency (echo-RTT), connection churn metrics

**Implementation Requirements & Constraints:**
- Server must reject frames from unmasked clients (RFC 6455 compliance)
- Close handshake must complete within 5 s or force-close

**Engineering Milestones (DoD):**
- [ ] Handshake succeeds with compliant clients (100% of Autobahn test suite basics); frame codec handles 1M fragmented messages with 0 errors
- [ ] Heartbeat detects dead connections < 2× interval; compression reduces payload ≥ 70% on text workloads

### 17.7 QUIC [x]
**Engineering Sub-tasks:**
- [ ] Implement QUIC transport: packet framing (long/short header), connection IDs, version negotiation
- [ ] Implement TLS 1.3 integration: handshake over QUIC crypto frames, 0-RTT/1-RTT keys
- [ ] Implement QUIC flow control: stream + connection windows, MAX_DATA/MAX_STREAM_DATA management
- [ ] Implement loss recovery: ACK frame processing, RTT estimation, retransmission, PTO timer
- [ ] Implement congestion control: NewReno baseline, CUBIC/BBR pluggable, ECN support

**Implementation Requirements & Constraints:**
- QUIC requires UDP; anti-amplification limit (3× validated address) enforced pre-handshake
- Connection IDs must be unpredictable (CSPRNG) and rotated on migration

**Engineering Milestones (DoD):**
- [ ] Handshake completes 1-RTT (< 100 ms LAN); loss recovery matches reference behavior (RTT estimate within 10%)
- [ ] Throughput ≥ 3 GB/s loopback; anti-amplification enforced in 100% of spoofed-source tests

---

## PHASE 18 — DEVOPS (9 modules)

### 18.1 Docker [x]
**Engineering Sub-tasks:**
- [ ] Implement Dockerfile set: runtime image (distroless/minimal), build image (toolchain), dev image
- [ ] Implement multi-stage builds: compile stage → runtime stage, artifact extraction, layer caching strategy
- [ ] Implement image hardening: non-root user, read-only rootfs, capability drop, seccomp profile
- [ ] Implement image CI: build matrix (arch), vulnerability scan (Trivy), size budget gate
- [ ] Implement runtime config: healthcheck, resource limits (CPU/mem), signal handling (PID 1)

**Implementation Requirements & Constraints:**
- Runtime image contains no compiler/toolchain; runs as non-root by default
- Image layer order maximizes cache hits (deps → code → config)

**Engineering Milestones (DoD):**
- [ ] Runtime image < 200 MB; vulnerability scan: 0 CRITICAL/HIGH in base image (gate enforced)
- [ ] Container starts < 3 s; healthcheck detects unhealthy state in 100% of fault injections

### 18.2 Docker Compose [x]
**Engineering Sub-tasks:**
- [ ] Implement compose stack definitions: service mesh (engine, gateway, worker, store, monitoring)
- [ ] Implement compose profiles: dev, test, prod-sim with per-profile env/config
- [ ] Implement dependency orchestration: health-check-gated startup ordering, restart policies
- [ ] Implement volume/persistence strategy: named volumes for state, bind-mounts for dev
- [ ] Implement compose tooling: `up/down/logs/exec` wrappers, one-off migration jobs

**Implementation Requirements & Constraints:**
- Compose is for dev/test only; production deployment uses orchestrator (K8s manifests generated)
- Resource defaults set per service (no unbounded memory)

**Engineering Milestones (DoD):**
- [ ] `docker compose up` brings stack healthy < 2 min; dependency ordering prevents race conditions in 100 restarts
- [ ] Profiles select correct config in 100% of cases; teardown leaves zero orphan volumes

### 18.3 GitHub Actions [x]
**Engineering Sub-tasks:**
- [ ] Implement CI workflow set: build, test (unit/integration), lint, security scan, benchmark, release
- [ ] Implement workflow matrices: Go versions × OS × arch; Python versions
- [ ] Implement caching strategy: Go module cache, pip cache, build cache with lockfile keys
- [ ] Implement workflow security: least-privilege tokens, pinned actions (SHA), secrets scoping
- [ ] Implement workflow observability: run duration trends, failure classification, artifact retention

**Implementation Requirements & Constraints:**
- All third-party actions pinned to commit SHAs (no floating tags)
- CI must be green before merge (required-status-checks policy)

**Engineering Milestones (DoD):**
- [ ] Full CI completes < 25 min; cache hit rate ≥ 80% for module/pip caches
- [ ] Zero unpinned actions (audit script passes); release workflow produces signed artifacts (cosign)

### 18.4 CI [x]
**Engineering Sub-tasks:**
- [ ] Implement CI pipeline stages: lint → build → unit → integration → e2e → security → benchmark → artifact
- [ ] Implement test sharding: parallel test split by package/file with balanced durations
- [ ] Implement failure handling: fast-fail on lint/build, test failure aggregation, flaky quarantine
- [ ] Implement CI gating: coverage thresholds, benchmark regression gate, license compliance
- [ ] Implement CI environment parity: containerized runners matching production base images

**Implementation Requirements & Constraints:**
- CI stages are deterministic: same commit → same result (no flaky gating)
- Secrets available only to protected branches/PRs from same repo

**Engineering Milestones (DoD):**
- [ ] Pipeline executes 100% of test suite; sharding imbalance ≤ 20% across shards
- [ ] Gate enforcement: 0 merges with failing checks (policy test); flaky rate < 0.5%

### 18.5 CD [x]
**Engineering Sub-tasks:**
- [ ] Implement CD pipeline: build → sign → test-in-staging → canary → progressive rollout
- [ ] Implement deployment strategies: blue-green, canary (traffic %), rolling (max-surge/unavailable)
- [ ] Implement release gates: health checks, SLO burn-rate check, manual approval for prod
- [ ] Implement artifact management: immutable versioned artifacts, promotion path (staging→prod)
- [ ] Implement release metadata: commit SHA, changelog, approval record, rollback target

**Implementation Requirements & Constraints:**
- Deployments are immutable: new artifact per release (no in-place mutation)
- Rollback target is always the previous verified artifact

**Engineering Milestones (DoD):**
- [ ] Canary detects regressions: auto-halt on SLO burn in 100% of injected-failure releases
- [ ] Deployment completes < 10 min for reference stack; zero-downtime verified (100% request success during rollout)

### 18.6 Monitoring [x]
**Engineering Sub-tasks:**
- [ ] Implement monitoring stack integration: metrics ingestion (Prometheus/OTLP), dashboards (Grafana)
- [ ] Implement SLI/SLO definitions: latency, availability, error-rate with burn-rate alerts
- [ ] Implement infrastructure metrics: CPU/mem/disk/network per node/container
- [ ] Implement application metrics: request rates, error rates, saturation (RED/USE)
- [ ] Implement monitoring as code: dashboard/alert definitions in repo (JSONnet/Terraform)

**Implementation Requirements & Constraints:**
- All SLOs have burn-rate alerts (fast + slow windows)
- Monitoring itself is monitored (dead-man's-switch metric)

**Engineering Milestones (DoD):**
- [ ] Metrics ingestion p95 < 10 s end-to-end; dashboards render < 2 s at 30-day ranges
- [ ] Alert on induced outage fires < 2 min (fast burn); zero missing metrics in 30-day soak

### 18.7 Logging [x]
**Engineering Sub-tasks:**
- [ ] Implement log pipeline: structured JSON logs → collector (agent) → store (Loki/ELK) → query
- [ ] Implement log levels in prod: INFO default, dynamic DEBUG per-module (runtime toggle)
- [ ] Implement log correlation: trace-id/request-id injection, cross-service log joins
- [ ] Implement log retention: tiered storage (hot/warm/cold), compliance retention policies
- [ ] Implement log security: redaction filters (PII/secrets), access control on log store

**Implementation Requirements & Constraints:**
- Logs are structured (JSON) with stable field names; no free-text-only logs
- Redaction happens at source (before emit) for secrets

**Engineering Milestones (DoD):**
- [ ] Log pipeline delivers ≥ 99.9% of events (loss test); redaction removes 100% of synthetic secrets
- [ ] Trace-correlated query returns full request path < 5 s; retention policies enforced in 100% of audits

### 18.8 Auto Deployment [x]
**Engineering Sub-tasks:**
- [ ] Implement auto-deploy triggers: tag push → staging, manual promotion → prod, hotfix fast-path
- [ ] Implement pre-deploy verification: smoke tests, migration dry-run, resource availability check
- [ ] Implement progressive delivery: canary analysis (metric-based), auto-promote/rollback decisions
- [ ] Implement deploy locking: concurrent-deploy prevention, maintenance-window enforcement
- [ ] Implement deploy notifications: status to chat/email, deploy record to audit log

**Implementation Requirements & Constraints:**
- Auto-deploy requires green CI + passing smoke tests; no human bypass without audit record
- Rollback decision is automatic on SLO burn (no human latency in failure path)

**Engineering Milestones (DoD):**
- [ ] Auto-deploy pipeline succeeds in 100% of green-CI releases; auto-rollback triggers < 3 min after SLO breach
- [ ] Deploy-lock prevents concurrent deploys in 100% of race tests; full deploy audit trail present

### 18.9 Rollback [x]
**Engineering Sub-tasks:**
- [ ] Implement rollback strategy: instant revert to previous artifact (blue-green) or version rollback (rolling)
- [ ] Implement state compatibility: backward-compatible migrations required (expand/contract pattern)
- [ ] Implement rollback verification: post-rollback health + smoke checks, traffic-shift validation
- [ ] Implement rollback triggers: automatic (SLO burn, error-rate spike) and manual (`deploy rollback`)
- [ ] Implement rollback drills: scheduled chaos rollback exercises with success metrics

**Implementation Requirements & Constraints:**
- Rollback must complete < 5 min (RTO target); data migrations must be reversible or expand/contract
- Rollback preserves data: no data loss across version boundaries (migration compatibility gate)

**Engineering Milestones (DoD):**
- [ ] Rollback RTO < 5 min in 100% of drills; zero data loss in rollback-with-migration tests
- [ ] Automatic rollback fires in 100% of induced regressions; post-rollback health checks pass before traffic restore

---

## PHASE 19 — OBSERVABILITY (6 modules)

### 19.1 Metrics [x]
**Engineering Sub-tasks:**
- [ ] Implement metrics library: counters, gauges, histograms (prometheus-style), summaries
- [ ] Implement metric registry: named registration, label sets, duplicate detection
- [ ] Implement exposition: `/metrics` endpoint (Prometheus text format), OTLP exporter
- [ ] Implement high-cardinality control: label budget enforcement, metric-limits policy
- [ ] Implement metric lifecycle: deprecation markers, stale-metric cleanup, metric-documentation requirement

**Implementation Requirements & Constraints:**
- Metrics must be lock-free on hot paths (atomic counters, striped histograms)
- Cardinality is bounded: label values validated against allowlists where applicable

**Engineering Milestones (DoD):**
- [ ] Metrics overhead < 100 ns/op (counter increment); exposition endpoint serves 10k series < 100 ms
- [ ] Registry rejects 100% of duplicate registrations; all metrics carry documentation (lint-enforced)

### 19.2 Tracing [x]
**Engineering Sub-tasks:**
- [ ] Implement tracing SDK: spans, span-context propagation, baggage, sampling policies
- [ ] Implement auto-instrumentation: HTTP, RPC, DB, queue clients (wrapper libraries)
- [ ] Implement trace processing: tail-sampling, span-to-metric conversion, trace-to-log correlation
- [ ] Implement OTLP export: gRPC/HTTP exporters, batching, retry with backoff, queue overflow policy
- [ ] Implement trace analysis: latency decomposition, critical-path highlighting, service-dependency graph

**Implementation Requirements & Constraints:**
- Trace context propagates across all async/queue boundaries (W3C format)
- Sampling decision consistent across a trace (head-based) or statistically sound (tail-based)

**Engineering Milestones (DoD):**
- [ ] Trace completeness: 100% of spans linked under 1% sampling; exporter survives 10× burst without blocking
- [ ] Latency decomposition accuracy ± 5% vs. manual instrumentation; dependency graph matches topology in 100% of tests

### 19.3 Health Checks [x]
**Engineering Sub-tasks:**
- [ ] Implement health-check framework: liveness, readiness, startup probes with distinct semantics
- [ ] Implement check catalog: dependency checks (DB, cache, GPU, disk), self-checks (goroutine leak, deadlock detector)
- [ ] Implement check aggregation: weighted status, degraded-mode reporting, check timeouts
- [ ] Implement probe endpoints: `/healthz`, `/readyz`, `/livez` with machine-readable detail (JSON)
- [ ] Implement check scheduling: periodic execution, staleness detection, failure-threshold policy

**Implementation Requirements & Constraints:**
- Liveness must not depend on external deps (only self); readiness gates traffic
- Checks bounded by hard timeouts; slow checks fail-closed for readiness

**Engineering Milestones (DoD):**
- [ ] Readiness correctly drains on induced dependency failure in 100% of cases; liveness restarts loop only on true deadlocks
- [ ] Check execution < 1 s each; probe endpoints respond p99 < 10 ms under load

### 19.4 Crash Reports
**Engineering Sub-tasks:**
- [ ] Implement crash capture: panic hook, stack trace (symbolized), goroutine dump, memory snapshot
- [ ] Implement report enrichment: version, config hash, environment, recent log tail, request context
- [ ] Implement report transport: secure upload (TLS, redaction), batching, deduplication (crash fingerprinting)
- [ ] Implement crash analytics: grouping (fingerprint), frequency, first/last seen, affected-version matrix
- [ ] Implement crash-response integration: alerting on new/critical crashes, regression detection on new versions

**Implementation Requirements & Constraints:**
- Crash reports are opt-in with user consent; all PII redacted before upload
- Crash handler must be async-signal-safe where possible (no locks in fatal path)

**Engineering Milestones (DoD):**
- [ ] Crash capture succeeds in 100% of induced panics (50 cases); fingerprint groups identical crashes ≥ 95% accurately
- [ ] Redaction removes 100% of synthetic PII; upload fails safe (never blocks shutdown)

### 19.5 Performance Dashboard [x]
**Engineering Sub-tasks:**
- [ ] Implement performance dashboard: golden signals (latency, traffic, errors, saturation) + engine metrics (FLOPs, memory)
- [ ] Implement deep-dive panels: op-level latency heatmap, memory timeline, kernel occupancy, queue depths
- [ ] Implement comparison mode: time ranges, versions, deployments side-by-side
- [ ] Implement anomaly overlay: auto-detected outliers highlighted with context
- [ ] Implement dashboard templating: per-model/per-backend/per-cluster parameterized dashboards

**Implementation Requirements & Constraints:**
- Dashboard queries are pre-aggregated for interactive latency (< 2 s at 90 days)
- All panels cite data source and collection interval

**Engineering Milestones (DoD):**
- [ ] Dashboard renders < 2 s p95 at 90-day ranges; anomaly overlay flags ≥ 80% of injected anomalies
- [ ] Panel values match raw metrics within 1% (aggregation verified); templating works for 100% of parameter combos

### 19.6 Alerting [x]
**Engineering Sub-tasks:**
- [ ] Implement alerting engine: rule evaluation (threshold, rate-of-change, anomaly), multi-window burn-rates
- [ ] Implement alert routing: severity tiers, escalation policies, on-call schedules, deduplication
- [ ] Implement alert lifecycle: firing → acknowledged → resolved, with auto-resolve on recovery
- [ ] Implement alert quality controls: runbook link required, alert-tuning review, noise-rate metrics
- [ ] Implement notification channels: chat, email, pager, webhook with templated payloads

**Implementation Requirements & Constraints:**
- Every alert has: severity, runbook, dashboard link, owner (lint-enforced in definitions)
- Alert evaluation is distributed-fault-tolerant: no duplicate firing (leader-election or sharding)

**Engineering Milestones (DoD):**
- [ ] Alert fires within 60 s of condition (fast window); zero duplicate alerts in failover test
- [ ] Alert noise: false-positive rate < 5% over 30 days; 100% of alerts have runbook links (policy gate)

---

## PHASE 20 — DOCUMENTATION (8 modules)

### 20.1 Architecture Docs [x]
**Engineering Sub-tasks:**
- [ ] Author architecture overview: system context (C4 L1), containers (L2), components (L3) per subsystem
- [ ] Document data flows: request lifecycles, tensor data flow, control-plane vs. data-plane separation
- [ ] Document cross-cutting concerns: security model, deployment topology, failure domains, scaling model
- [ ] Maintain decision log linkage: every architectural claim references ADRs
- [ ] Implement docs validation: diagram freshness check (linked code paths exist), review cadence (quarterly)

**Implementation Requirements & Constraints:**
- Architecture docs are living documents: updated in the same PR as the change
- Diagrams must be source-controlled (Mermaid/d2), not screenshots

**Engineering Milestones (DoD):**
- [ ] C4 diagrams cover 100% of major subsystems; quarterly review completed with dated sign-off
- [ ] Doc-linked code references valid in 100% (link-check CI); ADR coverage for all cross-layer interfaces

### 20.2 ADRs (Architecture Decision Records) [x]
**Engineering Sub-tasks:**
- [ ] Implement ADR template: context, decision, alternatives (≥ 2), consequences, compliance notes
- [ ] Establish ADR workflow: proposed → accepted/superseded, numbering, immutable history
- [ ] Require ADRs for: cross-layer interfaces, performance budgets, security posture, dependency adoption
- [ ] Implement ADR tooling: lint (required sections), index generation, supersede-chain validation
- [ ] Implement ADR review: architect sign-off, periodic re-evaluation (12-month expiry for time-boxed decisions)

**Implementation Requirements & Constraints:**
- ADRs are immutable once accepted (changes create new ADR with supersede link)
- Every ADR states measurable consequences (cost, latency, complexity)

**Engineering Milestones (DoD):**
- [ ] ADR coverage: 100% of cross-layer interface decisions; ADR lint passes in CI
- [ ] Supersede chains valid in 100% of ADR graph (no orphan successors); re-evaluation executed for 100% of expired ADRs

### 20.3 API Docs [x]
**Engineering Sub-tasks:**
- [ ] Generate API reference: Go (godoc), Python (pdoc/Sphinx), REST (OpenAPI 3.1) from source of truth
- [ ] Author API guides: quickstart, conceptual, how-to, tutorial tiers (diátaxis framework)
- [ ] Implement doc examples: runnable snippets (tested in CI), output-verified, version-tagged
- [ ] Implement API changelog: per-version diff, deprecation notices with removal dates
- [ ] Implement doc coverage enforcement: undocumented exported symbols block release

**Implementation Requirements & Constraints:**
- OpenAPI spec is code-generated (never hand-maintained); examples are executable
- Deprecated APIs carry removal version and migration path

**Engineering Milestones (DoD):**
- [ ] 100% of exported symbols documented; 100% of examples pass in CI
- [ ] OpenAPI spec validates (spectral) with zero errors; changelog covers 100% of API changes per release

### 20.4 Tutorials [x]
**Engineering Sub-tasks:**
- [ ] Author tutorial track: beginner (5), intermediate (5), advanced (5) — each with objective, steps, verification
- [ ] Implement tutorial verification: every tutorial runs end-to-end in clean container (CI job)
- [ ] Implement tutorial versioning: version-pinned against engine releases, compatibility matrix
- [ ] Implement tutorial assets: notebooks, sample datasets, expected-output fixtures
- [ ] Implement tutorial analytics: completion tracking (opt-in), stuck-point detection from issue tags

**Implementation Requirements & Constraints:**
- Tutorials must complete < 15 min each; prerequisites explicitly listed
- Expected outputs are deterministic (fixed seeds)

**Engineering Milestones (DoD):**
- [ ] 100% of tutorials pass CI in clean environment on every release; estimated completion times accurate ± 20%
- [ ] Tutorial coverage: all major features (≥ 80% of Phase 10–14 features)

### 20.5 Examples [x]
**Engineering Sub-tasks:**
- [ ] Build example corpus: per-feature examples (≥ 50), per-domain examples (CV/NLP/RL, ≥ 10), reference models (≥ 10)
- [ ] Implement example standards: README, requirements, run command, expected output, benchmark numbers
- [ ] Implement example CI: all examples build+run on every PR (parallel jobs, time-boxed)
- [ ] Implement example quality gates: style lint, determinism check (two runs identical), resource budget
- [ ] Implement example discoverability: index by feature/domain/difficulty, links from docs

**Implementation Requirements & Constraints:**
- Examples are self-contained (no external downloads beyond declared datasets)
- Resource budgets: every example declares time/memory caps

**Engineering Milestones (DoD):**
- [ ] 100% of examples pass CI; determinism holds for 100% (bit-identical second runs)
- [ ] Example corpus covers ≥ 90% of public API surface; every example has passing README instructions

### 20.6 Developer Guide [x]
**Engineering Sub-tasks:**
- [ ] Author dev guide: environment setup, build/test commands, architecture walkthrough, debugging guide
- [ ] Document contribution workflow: branch strategy, PR checklist, review expectations, CI gates
- [ ] Document internals: module map, key data structures (tensor, graph, IR), concurrency model
- [ ] Implement dev-tooling docs: formatter/linter/debugger/profiler usage with examples
- [ ] Implement onboarding path: week-1 plan, first-issue guide, mentor assignment process

**Requirements & Constraints:**
- Dev guide is tested: commands in guide run verbatim in clean env (doc-test)
- Guide updated on any workflow change (same-PR rule)

**Engineering Milestones (DoD):**
- [ ] Doc-test passes 100% of guide commands; new contributor completes first PR using guide in < 2 days (measured)
- [ ] Guide covers 100% of dev workflows; updated within same PR as workflow changes (audit sample 100%)

### 20.7 User Guide [x]
**Engineering Sub-tasks:**
- [ ] Author user guide: installation, configuration, CLI reference, model training/inference workflows
- [ ] Document operational runbooks: monitoring, scaling, troubleshooting, common error catalog
- [ ] Implement user-guide validation: CLI examples execute against real binary (E2E doc-test)
- [ ] Implement glossary and FAQ: terminology consistency, top-50 support questions answered
- [ ] Implement user-guide versioning: per-release snapshots, upgrade guides between versions

**Implementation Requirements & Constraints:**
- User guide targets operators without compiler background; jargon defined on first use
- All CLI examples are copy-paste runnable (no placeholders)

**Engineering Milestones (DoD):**
- [ ] E2E doc-test passes 100% of user-guide examples; FAQ reduces support tickets ≥ 20% (measured)
- [ ] Upgrade guides exist for every minor release with breaking changes; error catalog covers ≥ 90% of observed errors

### 20.8 Contribution Guide [x]
**Engineering Sub-tasks:**
- [ ] Author CONTRIBUTING: setup, coding standards, commit conventions, PR process, review SLA
- [ ] Define contribution types: bug, feature, docs, benchmark, research — with templates
- [ ] Implement CLA/DCO process: sign-off enforcement, license-header checks, IP clearance
- [ ] Document community standards: code of conduct, communication channels, escalation path
- [ ] Implement contributor tooling: issue labels, good-first-issue curation, contributor recognition

**Implementation Requirements & Constraints:**
- Contribution rules are CI-enforced (commit format, sign-off, lint) — not advisory
- Review SLA: first response < 2 business days

**Engineering Milestones (DoD):**
- [ ] CI enforces 100% of contribution rules (sign-off, format, lint); templates present for all contribution types
- [ ] Review SLA met ≥ 90% of PRs; good-first-issue list maintained with ≥ 20 open items

---

## PHASE 21 — TESTING (7 modules)

### 21.1 Unit Tests [x]
**Engineering Sub-tasks:**
- [ ] Implement unit test standard: every exported function ≥ 1 happy-path + ≥ 1 error-path test
- [ ] Build test utilities: seeded RNG, golden files, table-driven test harness, assertion helpers
- [ ] Implement boundary testing: empty/1-element/large inputs, min/max values, all dtypes
- [ ] Implement property-based tests (fast-check style) for invariants (shape, dtype, algebra laws)
- [ ] Implement mutation testing: mutation score ≥ 70% on core packages (ir, optimizer, runtime)

**Implementation Requirements & Constraints:**
- Unit tests are hermetic: no network/clock/FS dependencies (injectables)
- Test names state behavior (TestOp_Case_ExpectedResult convention)

**Engineering Milestones (DoD):**
- [ ] Coverage ≥ 85% core / ≥ 70% repo; mutation score ≥ 70% on Phase 1–5 packages
- [ ] Property tests: ≥ 1000 random cases per invariant with zero failures; test suite deterministic (seeded)

### 21.2 Integration Tests [x]
**Engineering Sub-tasks:**
- [ ] Implement integration suites: compiler pipeline (source → graph → exec), memory subsystem, distributed (multi-process)
- [ ] Implement contract tests: module interfaces, plugin API, RPC schemas (consumer-driven)
- [ ] Implement environment fixtures: containers for dependencies (DB, queue), network namespaces
- [ ] Implement integration observability: per-suite timing, failure artifacts (logs, traces) on failure
- [ ] Implement integration isolation: per-test env, cleanup verification (no resource leaks)

**Implementation Requirements & Constraints:**
- Integration tests may use real processes but must be parallel-safe (unique ports/paths)
- Failure artifacts auto-attached to CI logs

**Engineering Milestones (DoD):**
- [ ] Integration coverage: 100% of cross-module interfaces; contract tests catch 100% of injected API breaks
- [ ] Full integration suite < 10 min; zero leaked resources (cleanup audit) across 100 runs

### 21.3 Benchmark Tests [x]
**Engineering Sub-tasks:**
- [ ] Implement benchmark suite (per Phase 0.9): micro (per-op), macro (model), soak (duration)
- [ ] Implement benchmark CI gate: regression detection vs. baseline with statistical significance
- [ ] Implement benchmark environments: pinned hardware class, noise detection (CoV threshold), result normalization
- [ ] Implement benchmark corpora: fixed input datasets (seeded), model zoo with recorded baselines
- [ ] Implement benchmark reporting: automated PR comments with perf deltas, historical trend links

**Implementation Requirements & Constraints:**
- Benchmarks run on dedicated runners (no noisy neighbors); CoV < 3% required for gating
- Baselines are per-arch (amd64/arm64) and stored versioned

**Engineering Milestones (DoD):**
- [ ] Benchmark gate catches ≥ 95% of regressions > 5% with p < 0.01; false-positive rate < 5%
- [ ] Full benchmark suite < 20 min; PR comment posted on 100% of perf-affecting PRs

### 21.4 Fuzz Tests [x]
**Engineering Sub-tasks:**
- [ ] Implement fuzz targets: parsers, deserializers, config loaders, graph builders, tensor ops (shape/dtype inputs)
- [ ] Implement fuzz corpus management: seed corpus (≥ 10k inputs), crash regression corpus, minimization
- [ ] Implement fuzz CI: nightly 30-min runs, coverage-guided (go fuzz), crash triage automation
- [ ] Implement fuzz invariants: no panics, no OOM beyond budget, no hangs (timeout per input)
- [ ] Implement fuzz reporting: crash signatures, deduplication, severity classification

**Implementation Requirements & Constraints:**
- Fuzz targets must be deterministic and bounded (time/memory caps per input)
- Every crash becomes a regression test within 24 h (SLA)

**Engineering Milestones (DoD):**
- [ ] Fuzz targets cover 100% of parsers/deserializers; 0 known unfixed crashes (SLA met)
- [ ] Nightly fuzz achieves ≥ 50% edge coverage on target packages; crash-to-regression ≤ 24 h in 100% of cases

### 21.5 Stress Tests [x]
**Engineering Sub-tasks:**
- [ ] Implement stress suites: high-concurrency (10k goroutines/requests), memory pressure (near-OOM), deep graphs (100k nodes)
- [ ] Implement resource-exhaustion tests: FD limits, memory limits, CPU starvation, disk-full scenarios
- [ ] Implement backpressure validation: queues saturate gracefully (no unbounded growth, no crash)
- [ ] Implement soak tests: 24h continuous operation with leak detection (memory flatness)
- [ ] Implement chaos injection: random failures (kill, delay, corrupt) with SLO verification

**Implementation Requirements & Constraints:**
- Stress tests assert graceful degradation (errors, not crashes) under resource exhaustion
- Memory growth bound: < 1% per hour under steady load (leak threshold)

**Engineering Milestones (DoD):**
- [ ] Zero crashes in 100 stress scenarios; graceful degradation verified in 100% of exhaustion cases
- [ ] 24h soak: memory drift < 1%, error rate < 0.01%; chaos suite passes with SLO adherence ≥ 99%

### 21.6 Compatibility Tests
**Engineering Sub-tasks:**
- [ ] Implement version-compatibility matrix: engine × plugin API × config format × checkpoint format
- [ ] Implement cross-version tests: old checkpoints load on new engine; new exports load on old engine (within MAJOR)
- [ ] Implement platform matrix: OS (linux/darwin/windows), arch (amd64/arm64), Go versions (last 3)
- [ ] Implement dependency compatibility: BLAS/library version ranges, Python version support
- [ ] Implement compatibility reporting: matrix dashboard, failure triage with minimal-repro extraction

**Implementation Requirements & Constraints:**
- Compatibility policy documented: what is guaranteed (within MAJOR) vs. best-effort
- CI runs representative matrix nightly (full matrix weekly)

**Engineering Milestones (DoD):**
- [ ] 100% of guaranteed-compatibility cells pass nightly; policy violations caught in 100% of cases
- [ ] Old→new checkpoint round-trip succeeds for last 3 MAJOR versions; platform matrix green on 100% of supported cells

### 21.7 Long-running Stability Tests
**Engineering Sub-tasks:**
- [ ] Implement marathon tests: continuous training/inference loops (7-day target) with periodic checkpoints
- [ ] Implement stability metrics: memory flatness, throughput drift (< 5%), error accumulation, GC pressure
- [ ] Implement failure-injection marathons: random restarts, config reloads, plugin updates mid-run
- [ ] Implement long-run observability: hourly metric snapshots, trend analysis, anomaly flags
- [ ] Implement marathon reporting: stability certificate per release (7-day soak result)

**Implementation Requirements & Constraints:**
- Marathon runs on dedicated capacity; checkpoint every hour (resume capability mandatory)
- Stability criteria quantitative: throughput drift < 5%, memory drift < 1%, zero unrecoverable errors

**Engineering Milestones (DoD):**
- [ ] 7-day marathon completes with zero unrecoverable errors; drift within thresholds (certified per release)
- [ ] Resume-after-restart verified in 100% of injected restarts; marathon results archived with release artifacts

---

## PHASE 22 — RESEARCH (11 modules)

### 22.1 Transformer Internals [x]
**Engineering Sub-tasks:**
- [ ] Implement research harness: attention-pattern visualization, head-importance scoring (ablation), embedding PCA
- [ ] Implement transformer variants: RoPE variants, ALiBi, sliding-window attention, GQA/MQA
- [ ] Implement interpretability probes: probing classifiers, activation patching, circuit discovery tooling
- [ ] Implement scaling experiments: loss-vs-scale curves (Chinchilla-style), critical-batch-size estimation
- [ ] Implement evaluation suite: perplexity, downstream tasks, contamination-checked benchmarks

**Implementation Requirements & Constraints:**
- Research code is experimental (separate package); production paths unaffected
- All experiments are reproducible: seeds, configs, and datasets versioned

**Engineering Milestones (DoD):**
- [ ] Reproduce ≥ 3 published findings (e.g., scaling laws) within reported variance; experiment reproducibility verified by independent re-run
- [ ] Attention tooling correctly identifies known circuits on synthetic tasks (100% of injected patterns)

### 22.2 Mixture of Experts [x]
**Engineering Sub-tasks:**
- [ ] Implement MoE layers: top-k routing (softmax gating), expert FFNs, load-balancing losses (aux-loss, z-loss)
- [ ] Implement routing stability: expert-capacity factors, drop-policy, noise injection for exploration
- [ ] Implement MoE inference: expert-parallel dispatch, batched expert computation, expert caching
- [ ] Implement MoE analysis: router entropy, expert utilization histograms, expert-specialization clustering
- [ ] Implement MoE scaling: expert-count sweep, capacity-factor tuning, routing-collapse detection

**Implementation Requirements & Constraints:**
- Router must remain balanced: auxiliary loss weight tuned per model size (documented heuristics)
- Expert parallelism requires all-to-all collectives (Phase 12 integration points)

**Engineering Milestones (DoD):**
- [ ] MoE matches dense-model loss at equal FLOPs on 3 benchmarks (within 0.1%); load balance: max expert utilization ≤ 2× mean
- [ ] Routing collapse detected in 100% of induced-collapse cases; expert-parallel scales ≥ 8 experts with ≥ 70% efficiency

### 22.3 Diffusion Models [x]
**Engineering Sub-tasks:**
- [ ] Implement diffusion primitives: noise schedules (linear/cosine), DDPM/DDIM samplers, score-matching losses
- [ ] Implement training pipeline: latent diffusion (VAE encoder), conditioning mechanisms (classifier-free guidance)
- [ ] Implement samplers: DPM-Solver, ancestral sampling, deterministic (DDIM) with quality/speed tradeoff control
- [ ] Implement evaluation: FID, IS, CLIP-score pipelines with fixed reference statistics
- [ ] Implement acceleration research: distillation (progressive), latent-space shortcuts, caching of reuse features

**Implementation Requirements & Constraints:**
- Sampler determinism: fixed seed → identical images (verified)
- Evaluation statistics frozen per dataset (no recomputation drift)

**Engineering Milestones (DoD):**
- [ ] DDPM reproduces published FID within 5% on CIFAR-10-scale experiment; DDIM 20-step matches 1000-step quality within 10% FID
- [ ] Deterministic sampling verified (bit-identical across 3 runs); guidance scales produce monotonic quality change

### 22.4 Reinforcement Learning
**Engineering Sub-tasks:**
- [ ] Implement RL primitives: environments (gym-interface), replay buffers (prioritized), policy/value networks
- [ ] Implement algorithms: PPO, SAC, DQN with tuned hyperparameters and entropy regularization
- [ ] Implement reward infrastructure: reward shaping, normalization (running stats), reward-model interface (RLHF)
- [ ] Implement RL stability tooling: value-loss spikes detection, KL-constraint monitoring, advantage normalization
- [ ] Implement evaluation: sample-efficiency curves, return distributions, seed-statistics reporting

**Implementation Requirements & Constraints:**
- RL experiments require ≥ 5 seeds with mean±std reporting (no single-seed claims)
- Replay buffers must be memory-mapped for large-capacity runs

**Engineering Milestones (DoD):**
- [ ] PPO/SAC reproduce reference rewards on 3 standard environments within 10%; sample-efficiency curves match literature shape
- [ ] Zero hyperparameter sensitivity surprises: documented ranges tested; seed-variance reported for 100% of results

### 22.5 Graph Neural Networks
**Engineering Sub-tasks:**
- [ ] Implement GNN layers: GCN, GraphSAGE, GAT, message-passing framework (MPNN)
- [ ] Implement graph data structures: CSR-backed graphs, mini-batch sampling (neighbor sampler), graph augmentation
- [ ] Implement readout/pooling: global mean/sum, attention pooling, hierarchical pooling
- [ ] Implement GNN benchmarks: OGB-style datasets, transductive/inductive splits, leaderboard metrics
- [ ] Implement GNN scaling: subgraph training, distributed graph partitioning (METIS-style), large-graph inference

**Implementation Requirements & Constraints:**
- Message passing must support sparse adjacency (no dense N×N materialization)
- Neighbor sampling must be unbiased (documented sampling distribution)

**Engineering Milestones (DoD):**
- [ ] GCN/GAT match reference accuracy on Cora/PubMed within 1%; mini-batch training converges to within 2% of full-batch
- [ ] Sparse message passing: memory ≤ O(E) on 1M-edge graphs; neighbor sampler verified unbiased (distribution test, p > 0.05)

### 22.6 Compiler Theory
**Engineering Sub-tasks:**
- [ ] Implement research playground: new pass prototyping (SSA-based), pass-evaluation harness (compile-time/runtime tradeoff)
- [ ] Implement polyhedral research: affine loop analysis, tiling transformations, dependence polyhedra (experimental)
- [ ] Implement ML-guided compilation: cost-model learning (itinerary), learned policy for fusion/ordering decisions
- [ ] Implement formal-methods integration: SMT-based verification of rewrite rules (proving equivalence)
- [ ] Implement compilation research evaluation: PolyBench/TSVC benchmarks, speedup vs. -O2 baseline

**Implementation Requirements & Constraints:**
- Experimental passes isolated from production pipeline (feature-gated)
- ML cost models require held-out validation (no overfitting to training graphs)

**Engineering Milestones (DoD):**
- [ ] ≥ 2 research passes reach production quality (measured speedup ≥ 10% on benchmarks); SMT verification proves equivalence for ≥ 20 rewrite rules
- [ ] Learned cost model generalizes: held-out graph prediction error < 20%; polyhedral tiling beats -O2 on ≥ 50% of PolyBench

### 22.7 Operating Systems
**Engineering Sub-tasks:**
- [ ] Implement OS-awareness layer: CPU topology discovery, NUMA-aware allocation, huge-page support (madvise)
- [ ] Implement scheduler-OS interplay: cgroup awareness, CPU affinity control, ionice/nice policy hooks
- [ ] Implement kernel-bypass research: io_uring integration (async I/O), eBPF-based observability probes
- [ ] Implement memory-OS integration: mmap-backed tensor storage, transparent huge pages tuning
- [ ] Implement OS-level profiling: perf event access, scheduler-latency measurement, context-switch accounting

**Implementation Requirements & Constraints:**
- OS features degrade gracefully: unavailable features (e.g., io_uring) fall back to epoll
- Privilege requirements documented; unprivileged mode fully functional

**Engineering Milestones (DoD):**
- [ ] NUMA-aware allocation improves throughput ≥ 15% on 2-socket host; huge pages reduce TLB misses ≥ 30% on large-tensor workloads
- [ ] io_uring path achieves ≥ 1.2× epoll throughput on async I/O benchmark; graceful fallback verified on 5 emulated environments

### 22.8 Distributed Systems [x]
**Engineering Sub-tasks:**
- [ ] Implement consensus research: Raft-lite implementation with leader election, log replication, membership change
- [ ] Implement distributed scheduling research: gang scheduling, elasticity (dynamic worker sets), preemptive scheduling
- [ ] Implement consistency research: causal consistency for parameter servers, exactly-once semantics patterns
- [ ] Implement failure-semantics research: Byzantine fault tolerance (optional), partial-failure models, recovery verification
- [ ] Implement distributed evaluation: Jepsen-style linearizability checks, throughput/latency scaling curves

**Implementation Requirements & Constraints:**
- Consensus used only where required (cluster state); hot paths avoid consensus latency
- Exactly-once claims require idempotency infrastructure (verified by tests)

**Engineering Milestones (DoD):**
- [ ] Raft implementation passes correctness suite (leader election, log consistency) under 100 fault injections
- [ ] Linearizability verification passes on 3 critical operations; scaling curves show ≥ 70% efficiency to 8 nodes

### 22.9 Database Internals
**Engineering Sub-tasks:**
- [ ] Implement storage-engine research: LSM-tree vs. B-tree evaluation, write-ahead log, compaction strategies
- [ ] Implement indexing research: vector index (HNSW/IVF) for embedding search, ANN recall/latency curves
- [ ] Implement query-engine research: vectorized execution, predicate pushdown, join algorithms (hash/merge)
- [ ] Implement checkpoint-store research: content-addressed storage, delta encoding, garbage collection
- [ ] Implement database benchmarking: YCSB-style workloads, TPC-class throughput, tail-latency analysis

**Implementation Requirements & Constraints:**
- Checkpoint storage is append-only with GC; no in-place mutation of committed data
- ANN indexes declare recall targets (e.g., recall@10 ≥ 0.95)

**Engineering Milestones (DoD):**
- [ ] LSM write throughput ≥ 2× B-tree on write-heavy YCSB; compaction maintains read amplification ≤ 10
- [ ] Vector index achieves recall@10 ≥ 0.95 at ≥ 10× brute-force speed on 1M-vector benchmark; WAL survives 100% of crash-recovery tests

### 22.10 Linux Kernel
**Engineering Sub-tasks:**
- [ ] Implement kernel-interface research: eBPF programs for tracing engine events (uprobes), XDP for network fast-path
- [ ] Implement syscall optimization: io_uring for storage/network, memfd_create for zero-share buffers, userfaultfd for lazy loading
- [ ] Implement kernel-tuning research: scheduler policies (SCHED_FIFO for critical threads), TCP tuning, transparent huge pages
- [ ] Implement kernel observability: ftrace/perf integration, kernel-level latency attribution
- [ ] Implement kernel-module feasibility study: device-driver interface for custom accelerators (research only)

**Implementation Requirements & Constraints:**
- eBPF programs are CO-RE (compile-once-run-everywhere) with kernel-version guards
- Kernel research is opt-in: default deployments use unprivileged fallbacks

**Engineering Milestones (DoD):**
- [ ] eBPF tracing adds < 2% overhead and captures 100% of instrumented engine events; uprobe attachment verified across 3 kernel versions
- [ ] io_uring storage path ≥ 1.3× thread-per-op baseline; userfaultfd lazy loading reduces startup memory ≥ 40% on large checkpoints

### 22.11 High-Performance Computing [x]
**Engineering Sub-tasks:**
- [ ] Implement HPC primitives: MPI-style collectives (all-reduce, broadcast, all-to-all) over TCP/IB-capable transport
- [ ] Implement HPC algorithms: blocked matrix algorithms, parallel FFT (research), scan primitives
- [ ] Implement HPC benchmarks: HPL-style DGEMM, STREAM memory bandwidth, OSU micro-benchmarks
- [ ] Implement HPC job integration: batch-scheduler adapters (SLURM), node allocation, elastic scaling
- [ ] Implement HPC correctness: deterministic reduction modes, reproducible summation (Kahan/compensated)

**Implementation Requirements & Constraints:**
- Collectives must support both blocking and non-blocking semantics
- Deterministic mode uses reproducible reductions (fixed tree order)

**Engineering Milestones (DoD):**
- [ ] DGEMM achieves ≥ 60% peak on reference cluster; all-reduce scales ≥ 85% efficiency to 16 nodes
- [ ] Reproducible summation: identical results across 1/2/4/8 nodes (bitwise) on 100 tests; STREAM bandwidth ≥ 80% of theoretical

---

## PHASE 23 — LEADERSHIP (8 modules)

### 23.1 Architecture Reviews
**Engineering Sub-tasks:**
- [ ] Establish architecture review board (ARB) cadence: weekly design reviews, monthly deep-dives
- [ ] Implement review process: design-doc submission (template), ARB feedback loop, approval gate for cross-layer changes
- [ ] Implement review quality standards: ≥ 2 reviewer sign-offs, alternatives analysis required, performance/security assessment mandatory
- [ ] Implement review tracking: decision register, action items with owners/dates, follow-up verification
- [ ] Implement review metrics: review latency (p50/p95), rework rate, post-review defect rate

**Implementation Requirements & Constraints:**
- No cross-layer interface ships without ARB approval (CI-enforced: ADR link required)
- Review latency budget: p95 < 5 business days

**Engineering Milestones (DoD):**
- [ ] 100% of cross-layer changes have ARB record; post-review defect rate < 5% (measured over quarters)
- [ ] Review latency within budget ≥ 90% of cases; action-item closure rate ≥ 95%

### 23.2 Code Reviews [x]
**Engineering Sub-tasks:**
- [ ] Define code-review standard: checklist (correctness, tests, perf, security, docs), review depth by risk tier
- [ ] Implement review tooling: required reviewers (CODEOWNERS), size limits (≤ 400 LOC/PR guidance), review-bot checks
- [ ] Implement review SLAs: first response < 1 day, approval cycle < 2 days, escalation path for blocked PRs
- [ ] Implement review analytics: review coverage (100% of PRs), comment sentiment, defect-catch rate, knowledge distribution
- [ ] Implement review training: calibration sessions, exemplar reviews, reviewer onboarding

**Implementation Requirements & Constraints:**
- All PRs require ≥ 1 approval + green CI (no self-merge to main)
- Review comments are constructive and specific (no vague rejections)

**Engineering Milestones (DoD):**
- [ ] 100% of merged PRs have review record; defect-catch rate ≥ 30% (injected-bug audit)
- [ ] Review SLA met ≥ 90%; knowledge concentration: top-5 reviewer share < 50% of reviews (bus-factor control)

### 23.3 Release Planning
**Engineering Sub-tasks:**
- [ ] Establish release cadence: monthly minor, quarterly major, LTS track definition
- [ ] Implement release process: scope freeze → RC → bug-fix → GA with entry/exit criteria per stage
- [ ] Implement release risk management: risk register, mitigation owners, go/no-go checklist
- [ ] Implement release communication: changelog, upgrade notes, deprecation schedule announcement
- [ ] Implement release metrics: defect escape rate, release-cycle time, rollback rate

**Implementation Requirements & Constraints:**
- RC must pass full test + benchmark + security gates; zero known-critical bugs at GA
- Deprecations require ≥ 1 minor version of warning before removal

**Engineering Milestones (DoD):**
- [ ] Release cadence met ≥ 90% (on-time); rollback rate < 5% of releases
- [ ] Defect escape rate < 2% post-GA; 100% of releases have complete changelog + upgrade notes

### 23.4 Roadmap Planning [x]
**Engineering Sub-tasks:**
- [ ] Implement roadmap governance: quarterly planning cycle, input collection (customer/engineering/research), prioritization framework (RICE/WSJF)
- [ ] Implement roadmap artifact: per-quarter themes, epics, measurable success criteria, dependency mapping
- [ ] Implement roadmap tracking: weekly progress review, milestone burn-down, slip-forecast (Monte Carlo)
- [ ] Implement roadmap communication: published roadmap (internal + external), change-log of roadmap revisions
- [ ] Implement roadmap retrospective: accuracy review (planned vs. shipped), calibration of estimates

**Implementation Requirements & Constraints:**
- Roadmap items carry quantifiable success criteria (no vague goals)
- Scope changes require re-approval at governance forum

**Engineering Milestones (DoD):**
- [ ] Quarterly roadmap delivery rate ≥ 80% (committed items shipped); estimate accuracy within ± 30% for ≥ 70% of items
- [ ] 100% of roadmap items have measurable success criteria; roadmap updated and published quarterly

### 23.5 Technical Decision Records [x]
**Engineering Sub-tasks:**
- [ ] Implement TDR process distinct from ADRs: tactical decisions (libraries, patterns, tooling) logged lightweight
- [ ] Implement TDR template: context, options, decision, rationale, review date
- [ ] Implement TDR index: searchable registry linked from code (decision comments with TDR refs)
- [ ] Implement TDR review: 6-month re-evaluation, automatic flags for expired decisions
- [ ] Implement TDR metrics: decision latency, reversal rate, coverage of key choices

**Implementation Requirements & Constraints:**
- TDRs are lightweight (≤ 1 page); ADRs for architecture, TDRs for tactics
- Code references TDR ids for non-obvious choices (grep-enforced convention)

**Engineering Milestones (DoD):**
- [ ] 100% of dependency/tooling adoptions have TDRs; reversal rate < 10% (decision quality signal)
- [ ] Decision latency p50 < 3 days; TDR index covers 100% of registered decisions with valid links

### 23.6 Team Standards
**Engineering Sub-tasks:**
- [ ] Codify engineering standards: style guide, API design rules, error-handling policy, testing policy, security baseline
- [ ] Implement standards automation: linters/formatters enforce style; CI gates enforce test/security policy
- [ ] Implement standards evolution: RFC process for standard changes, community vote, versioned standards
- [ ] Implement standards education: onboarding module, standards quiz, exemplar repos
- [ ] Implement standards compliance metrics: automated compliance score, exception registry with expiry

**Implementation Requirements & Constraints:**
- Standards are enforced by tools first, humans second (no manual-only rules)
- Exceptions are time-boxed (≤ 6 months) and tracked

**Engineering Milestones (DoD):**
- [ ] Automated enforcement covers ≥ 90% of standards (lint/CI); compliance score ≥ 95% per quarter
- [ ] Exception registry: 100% of exceptions have expiry dates; zero expired exceptions active

### 23.7 Mentoring
**Engineering Sub-tasks:**
- [ ] Implement mentoring program: pairing (senior-junior), growth plans, competency matrix (levels L1–L5)
- [ ] Implement knowledge-transfer rituals: tech-talks (biweekly), paper-reading club, architecture walkthroughs
- [ ] Implement mentoring metrics: promotion velocity, internal-mobility rate, 360-feedback trends
- [ ] Implement onboarding pipeline: 30/60/90-day plans, first-PR guidance, mentor assignment SLA
- [ ] Implement community building: internal guilds (compiler/infra/ML), conference-talk support, open-source contributions

**Implementation Requirements & Constraints:**
- Mentoring is structured: goals + cadence (≥ 2 sessions/month) + written growth plan
- Onboarding mentor assigned within 24 h of join

**Engineering Milestones (DoD):**
- [ ] 100% of new engineers have mentor within 24 h; onboarding-to-first-merge ≤ 10 days (p50)
- [ ] Promotion velocity: ≥ 1 promotion per engineer per 18 months (L1–L4); engagement score ≥ 4/5 in surveys

### 23.8 Milestone Reviews
**Engineering Sub-tasks:**
- [ ] Implement milestone review process: weekly status, monthly milestone review, quarterly executive review
- [ ] Define review artifacts: milestone scorecard (scope/schedule/quality/risk), demo of working system, metrics dashboard
- [ ] Implement go/no-go criteria: quantitative gates (test pass, perf, security) per milestone
- [ ] Implement corrective-action loop: slip analysis, root-cause (5-whys), recovery plan with owner
- [ ] Implement historical tracking: milestone accuracy (planned vs. actual), velocity trends, prediction model refinement

**Implementation Requirements & Constraints:**
- Milestone reviews are evidence-based: working software demonstrated, not slide-only
- Every slip has a documented root-cause within 1 week

**Engineering Milestones (DoD):**
- [ ] 100% of milestones have scorecards and go/no-go records; slip root-causes documented within 1 week in 100% of cases
- [ ] Milestone prediction accuracy ≥ 80% (± 2 weeks); recovery plans executed in 100% of red milestones

---

*End of ASTROVOX MASTER IMPLEMENTATION CHECKLIST - 24 phases, 229 modules, all directives decomposed.*

