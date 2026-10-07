# Astrovox Tensor Engine — Architectural Design Specification & Multi-Phase Implementation Roadmap

| Field | Value |
|---|---|
| System | Astrovox Tensor Engine (ATE) |
| Prerequisite | Core Utilities Package (`astrovox/internal/*`) |
| Module | `github.com/astrovox/astrovox` |
| Language | Go 1.27 (pure stdlib, zero external dependencies) |
| Stages | 10 (Tensor Core → Documentation) |

**Design principles**
1. Zero-copy by default: views, broadcasting, and slicing never allocate.
2. Explicit ownership: storage is shared between views; GC handles reclamation.
3. Determinism: fixed iteration order and reduction tree per thread count.
4. Layered pipeline: `tensor` → `tensor/math` → `autograd` → `compiler` → `runtime` → `kernels`.
5. Every op is benchmarked; every kernel is registered and dispatched through the registry.

---

## Prerequisite — Core Utilities Package

Layout: `astrovox/internal/{logger,config,errors,utils,benchmark,profiler,validator,filesystem,version}`

### logger — Structured Logger
**Architecture:** Async ring-buffer logger. Producers append structured records (level, time, message, fields) to a lock-free MPMC queue; a single drain goroutine serializes to JSON/console sinks. Role: sole logging facade for all engine packages.
**Technical details:** Level enum (`Debug…Fatal`); `Field` struct (key, value, redact flag); ring buffer sized 2^16; atomic epoch counters for drop accounting; sink interface (`io.Writer` adapters); per-module filter map. Low-level: buffer pooling via `sync.Pool`, no allocation per record on steady state.
**Challenges/bottlenecks:** sink backpressure (policy: drop-oldest with counter), Fatal flush-before-exit, field redaction overhead.
**Integration:** All packages import `internal/logger`; CLI wires sinks from config.
**Verification:** unit (level filtering, field redaction, JSON shape), stress (1M records, drop counter exactness), benchmark (ns/record, throughput ≥ 1M rec/s).

### config — Configuration Loader (YAML/JSON)
**Architecture:** Layered config: defaults → file (JSON or YAML subset) → environment (`ASTROVOX_*`) → explicit overrides. Role: single source of runtime settings.
**Technical details:** Typed schema structs with `mapstructure`-style tags (custom reflect walker); minimal YAML subset parser (indent-based, maps/lists/scalars) to remain dependency-free; JSON via `encoding/json`; hot-reload via file watcher with atomic pointer swap (`atomic.Pointer`).
**Challenges/bottlenecks:** YAML subset correctness, precedence bugs, hot-reload races.
**Integration:** `config.Load(path)` used by CLI and engine init; env mapping `ASTROVOX_SEC_KEY`.
**Verification:** unit (precedence matrix, malformed inputs, fuzzed YAML), property tests (random schema round-trips), benchmark (parse 1MB config).

### errors — Custom Error System
**Architecture:** Typed error taxonomy with stable integer codes, structured context fields, and `errors.Is/As` compatibility. Role: engine-wide error contract.
**Technical details:** `Error` struct (code, message, op, cause, fields map); sentinel registry; `Wrap/WithField/WithOp`; lazy message formatting; redaction hooks.
**Challenges/bottlenecks:** code stability (never renumber), allocation on hot error paths (lazy strings).
**Integration:** All exported APIs return `*errors.Error`; CLI maps codes to exit codes.
**Verification:** unit (wrapping chains, code registry), fuzz (round-trip marshal), benchmark (wrap cost).

### utils — Shared Utilities
**Architecture:** Generic helpers: `Min/Max/Clamp` (generics), seeded RNG, content hashing (xxHash-style FNV-1a), bit tricks, `AllocsPerRun` wrappers. Role: eliminate per-package utility drift.
**Technical details:** `Rand` with deterministic seed; `Hash32/Hash64`; `Pow2` alignment helpers; `SyncOnce`-guarded globals.
**Challenges/bottlenecks:** none significant; keep allocation-free.
**Integration:** imported by all engine packages.
**Verification:** unit (edge cases), property tests (hash determinism, clamp laws).

### benchmark — Benchmark Helper
**Architecture:** Statistical benchmark harness: warmup, N timed iterations, outlier handling, percentile computation, CoV, baseline comparison with significance gating. Role: Stage 8 infrastructure.
**Technical details:** monotonic clock (`time.Now` → `runtime nanotime`), fixed workload seeds, per-run environment capture (GOARCH, GOMAXPROCS), JSON result export, `benchstat`-compatible output.
**Challenges/bottlenecks:** timer overhead, GC interference (control via `runtime.GC()` between runs).
**Integration:** every engine package exposes `Benchmark*` funcs using this harness; CI gates on p95 regression > 5%.
**Verification:** unit (percentile math, outlier rejection), self-benchmark.

### profiler — Simple Profiler
**Architecture:** Scoped profiler: `Start(name)`/`Stop` pairs recorded into per-thread ring buffers; aggregation into inclusive/exclusive times, call counts, memory snapshots (`runtime.ReadMemStats`). Role: Stage 7/8 observability.
**Technical details:** goroutine-local storage via context keys; hierarchical spans; 1 Hz time-series capture; pprof-compatible export.
**Challenges/bottlenecks:** overhead < 50 ns/span; goroutine correlation.
**Integration:** runtime executor wraps each op execution in a span.
**Verification:** unit (nesting, aggregation), benchmark (overhead measurement).

### validator — Validation Library
**Architecture:** Composable rule engine: `Rule` (predicate + message), `Schema` (field rules), mode flags (fast/deep). Role: input validation for config, shapes, dtypes, graph attrs.
**Technical details:** rule combinators (`Required`, `Range`, `Enum`, `Regex`, `Custom`); error aggregation (all failures, not first); JSON Schema export.
**Challenges/bottlenecks:** reflection cost (cached type info), O(n) deep validation.
**Integration:** tensor shape/dtype validation, config validation, graph attribute validation.
**Verification:** unit (100% rule coverage), fuzz (rule engine invariance).

### filesystem — File Utilities
**Architecture:** Atomic file ops: write-to-temp + rename, dir walk with filters, copy with progress, temp-dir lifecycle. Role: checkpoint/serialization I/O.
**Technical details:** `AtomicWrite` (fsync option), `Walk` (symlink policy), `Copy` (32KB buffered, `io.Copy`), `TempDir` (auto-cleanup via finalizer + explicit).
**Challenges/bottlenecks:** Windows rename-over-existing semantics (use `os.Rename` fallback chain), fsync cost.
**Integration:** tensor serialization, checkpoint manager, config loader.
**Verification:** unit (atomicity under injected failures), integration (large-file copy), benchmark (copy throughput).

### version — Environment/Semver Loader
**Architecture:** Semantic version parsing/comparison/constraints + runtime environment report (Go version, GOOS/GOARCH, CPU summary, env vars with prefix). Role: compatibility gating (plugins, checkpoints, IR).
**Technical details:** `Version` struct (MAJOR.MINOR.PATCH+prerelease), constraint parser (`^1.2.0`, `>=…<…`), precedence per semver 2.0; env loader (`LoadEnv(prefix)` → map).
**Challenges/bottlenecks:** prerelease ordering rules; constraint solver edge cases.
**Integration:** module registry, checkpoint loader, `astrovox version` CLI.
**Verification:** unit (semver test suite from spec), property tests (constraint satisfaction), fuzz (malformed versions).

---

## Stage 1 — Tensor Core

### 1.1 Tensor Data Structures — `tensor/tensor.go`
**Architecture:** `Tensor` = metadata (shape, strides, dtype) + `Storage` (aligned byte buffer) + element offset. Views share `*Storage`. Role: fundamental data carrier.
**Technical details:**
- `Storage { data []byte; dtype DType; numel int; align int }` — 64-byte aligned allocation (`make([]byte, n+63)` + offset rounding).
- `Tensor { st *Storage; offset int; shape Shape; strides []int }` — strides in element units.
- Contiguity check: `isContiguous()` via stride scan (row-major expectation).
- Element access: `Get(idx...)`/`Set(val, idx...)` with bounds + dtype switch; typed bulk accessors via `unsafe.Slice` (`Float32() []float32` etc.) — zero-copy views over the byte buffer.
- Reference semantics: views pin storage; no explicit free (GC).
**Challenges/bottlenecks:** alignment arithmetic correctness; unsafe alias hazards (documented contract: views must not outlive mutations they observe); dtype-switch cost in Get/Set (acceptable — bulk ops use typed slices).
**Integration:** every stage consumes `*Tensor`; serializer writes storage bytes.
**Verification:** unit (creation, alignment assertions, view aliasing), property tests (random views vs. reference indexing), fuzz (bounds), benchmark (element access, view creation).

### 1.2 Multi-dimensional Indexing
**Architecture:** linear↔multi-index conversion with strides; negative-index normalization; advanced indexing (integer arrays, boolean masks) producing copies.
**Technical details:** `LinearIndex(multi)` = Σ idxᵢ·strideᵢ; `Unravel(index, shape)` via divmod chain; mask ops single-pass with prefix-sum sizing.
**Challenges/bottlenecks:** advanced-indexing result-shape computation (NumPy semantics); O(n) mask pass.
**Integration:** ops/iterator use linear indexing internally.
**Verification:** unit vs. NumPy-derived golden cases; property tests (round-trip linear↔multi).

### 1.3 Broadcasting — `tensor/broadcast/`
**Architecture:** right-aligned shape reconciliation with dim-1 expansion (stride-0 virtual expansion, never materialized).
**Technical details:** `BroadcastShapes(a, b)` pure function with per-dim diagnostics; `BroadcastStrides(shape, target)` → stride-0 entries; integration into iterator plan.
**Challenges/bottlenecks:** mismatch diagnostics; rank-0 (scalar) broadcasting.
**Integration:** binary ops, reductions (keepdim), iterator.
**Verification:** unit (10k NumPy-equivalent cases incl. failures), benchmark ((1024,1)+(1,1024) → 0 extra alloc).

### 1.4 Views — `tensor/` (view constructors)
**Architecture:** zero-copy derived tensors: `ReshapeView`, `TransposeView`, `SliceView`, `ExpandView`; `IsView()`, `Base()` chain.
**Technical details:** stride arithmetic only; storage pinning via shared pointer; writability rules (overlapping views flagged).
**Challenges/bottlenecks:** alias detection (O(dims) overlap test per pair).
**Integration:** reshape/transpose/slicing return views when possible.
**Verification:** `AllocsPerRun == 0` tests; aliasing suite.

### 1.5 Slicing
**Architecture:** `Slice(begins, ends, steps)` → view (step ±1) or materialized copy (|step|>1 handled as strided view too — Go can express it via strides).
**Technical details:** negative-step = reversed view (stride negation); `Split`, `Chunk`, `Gather`, `Scatter`.
**Challenges/bottlenecks:** negative strides interacting with offset computation.
**Integration:** iterator handles arbitrary strides.
**Verification:** unit (300 permutations vs. reference), benchmark.

### 1.6 Reshape — `tensor/reshape/`
**Architecture:** `Reshape(shape)` with `-1` inference; zero-copy when strides permit, else `Contiguous()` fallback copy.
**Technical details:** `InferShape(old, new)` pure function; feasibility test: existing strides must be compatible with new shape in row-major order (single-pass walk).
**Challenges/bottlenecks:** reshape feasibility on non-contiguous tensors (conservative → copy).
**Integration:** compiler uses reshape-feasibility for fusion decisions.
**Verification:** property test (10k shape pairs); benchmark (zero-copy < 1 µs on 100M elements).

### 1.7 Transpose — `tensor/transpose/`
**Architecture:** `Transpose(d0, d1)` and `Permute(dims)` as stride-swap views; materialized `TiledTranspose` for cache efficiency.
**Technical details:** permutation validation (bijective); blocked transpose (block ≤ L2/3, auto-detected cache sizes).
**Challenges/bottlenecks:** tiled transpose block sizing; matmul auto-transpose fusion.
**Integration:** GEMM selects transposed variants (no explicit transpose).
**Verification:** unit (permutation sweep), benchmark (≥ 20 GB/s on 4096² fp32).

### 1.8 Dtype System — `tensor/dtype.go`
**Architecture:** `DType` enum + size table + promotion lattice + op-dtype compatibility matrix.
**Technical details:** `float16/32/64, bfloat16, int8/16/32/64, uint8/16/32/64, bool, complex64/128`; `Promote(a,b)`; `Size()`; `Zero()`; cast with saturation policy.
**Challenges/bottlenecks:** bf16↔fp32 conversion (bit manipulation, round-to-nearest-even); promotion correctness.
**Integration:** ops consult promotion before dispatch; serializer encodes dtype code.
**Verification:** unit (promotion lattice 16×16), property tests (cast round-trips).

### 1.9 Memory Alignment
**Architecture:** allocator enforces 64-byte alignment; per-op alignment requirements declared in kernel descriptors.
**Technical details:** aligned alloc via offset rounding; SIMD kernels assert alignment (fallback to unaligned path otherwise).
**Challenges/bottlenecks:** alignment waste ≤ 63 B; view offsets breaking base alignment (kernel checks effective address).
**Integration:** memory package (Stage 3) provides `AlignedAlloc`.
**Verification:** assertion test over 1M allocations; misalignment fallback test.

### 1.10 Serialization — `tensor/serialize.go`
**Architecture:** binary format v1: magic `ASTV`, format version, dtype code, rank, shape, strides, layout flags, xxHash64 checksum, payload.
**Technical details:** deterministic byte output (content-addressable); streaming save/load for > RAM tensors; mmap load path; endianness handling.
**Challenges/bottlenecks:** checksum cost (SIMD-accelerated FNV); version migration.
**Integration:** checkpoints, IPC, ONNX export path.
**Verification:** unit (round-trip dtype×rank matrix), fault injection (bit-flip detection), benchmark (≥ 2 GB/s).

---

## Stage 2 — Math Library (`tensor/math/`)

### 2.1 BLAS-like Operations
**Architecture:** Level 1–3 facades with pure-Go implementations and backend hook points. Role: numerical backbone.
**Technical details:** `Axpy, Dot, Nrm2, Scal, Gemv, Ger, Gemm, Trsm`; dispatcher selects native vs. registered backend kernel.
**Challenges/bottlenecks:** non-contiguous inputs (copy-to-contiguous with layout flags).
**Integration:** matmul/conv/attention consume these.
**Verification:** conformance suite vs. reference (1e-6 fp32 / 1e-12 fp64 tolerance).

### 2.2 Matrix Multiplication — `tensor/math/gemm.go`
**Architecture:** `MatMul(a, b)` → shape validation (contracting dims) → GEMM path selection.
**Technical details:** register-blocked micro-kernel (MR×NR tiles), panel packing (A/B), macro-kernel block factorization (MC×KC×NC from detected cache sizes), transposed variants, bias-add and ReLU fusion flags, batched GEMM.
**Challenges/bottlenecks:** cache-block auto-tuning; thread-parallel determinism (fixed partitioning when deterministic flag set).
**Integration:** Stage 6 compiler lowers matmul to GEMM+layout ops.
**Verification:** unit (500 (M,N,K) incl. edge 1×N, M×1), benchmark (SGEMM ≥ 8 GFLOP/s scalar baseline; ≥ 80% of roofline estimate).

### 2.3 GEMM Optimization
**Architecture:** tiling search over cache hierarchy (L1/L2/L3 detected at init), stored in per-host tuning file.
**Technical details:** micro-kernel unrolling, FMA chains via `math.FMA`, prefetch hints; AVX2 dispatch point (function-pointer table, scalar fallback).
**Challenges/bottlenecks:** tuning cost (calibration shapes), portability.
**Integration:** kernel registry (Stage 5) hosts GEMM variants.
**Verification:** benchmark suite; auto-tune convergence.

### 2.4 SIMD Kernels — `tensor/math/simd.go`
**Architecture:** dispatch layer: CPU feature detection → kernel function table; scalar fallback always available.
**Technical details:** `VecAdd, VecMul, Dot, Sum, Max, Exp, Tanh` kernels; masked tail handling; alignment prologue; ISA dispatch table (amd64 baseline = AVX2-class heuristics, arm64 = Neon). Pure-Go tight loops are auto-vectorized by the compiler; hand-written assembly plugs into the same registry.
**Challenges/bottlenecks:** feature detection without cgo (runtime.GOARCH + OS queries); tail correctness.
**Integration:** all elementwise/reduction kernels route through dispatch.
**Verification:** known-answer tests per kernel; alignment torture tests; benchmark (≥ 8× scalar on 256-bit-class paths where available).

### 2.5 Vector Operations
**Architecture:** elementwise unary/binary on typed slices with iterator fusion.
**Technical details:** `Add, Sub, Mul, Div, Neg, Scale, Pow, Min, Max, Clamp`; fused `AddMul`, `LinSpace`; NaN/Inf propagation per IEEE 754.
**Challenges/bottlenecks:** division-by-zero semantics; denormal flush policy.
**Integration:** ops package delegates here.
**Verification:** unit (edge values), benchmark (≥ 10 GB/s per core).

### 2.6 Convolution — `tensor/math/conv.go`
**Architecture:** Conv1d/2d/3d with strategy selection: direct (small kernels) vs. im2col+GEMM (large).
**Technical details:** padding/stride/dilation/groups; NHWC/NCHW layouts; Winograd-ready hook; shape inference at construction.
**Challenges/bottlenecks:** im2col memory blowup (blocked im2col); group conv bookkeeping.
**Integration:** model engine layers use conv primitives.
**Verification:** unit vs. naive direct convolution (rel. error < 1e-5), benchmark (im2col+GEMM ≥ 2× direct for 3×3 kernels).

### 2.7 FFT — `tensor/math/fft.go`
**Architecture:** radix-2 iterative Cooley-Tukey; zero-pad to power of two; 1D/2D; real-input optimization (RFFT via complex packing).
**Technical details:** bit-reversal permutation, butterfly stages with precomputed twiddle tables; inverse via conjugation trick; O(n log n).
**Challenges/bottlenecks:** twiddle table reuse; non-power-of-two fallback (Bluestein stub → zero-pad with warning).
**Integration:** spectral ops, audio/science tooling.
**Verification:** unit vs. direct DFT on 100 random vectors (error < 1e-9), benchmark (≥ 50M points/sec).

### 2.8 Reduction Kernels — `tensor/reduce/`
**Architecture:** parallel tree reduction with per-thread partials; associative-order determinism.
**Technical details:** `Sum, Mean, Var, Std, Min, Max, Prod, Norm, All, Any, ArgMin, ArgMax, CumSum, CumProd`; Welford variance; `LogSumExp` (max-shift); dim-masked traversal; keepdim.
**Challenges/bottlenecks:** float reduction order (fixed per thread count); Welford vs. naive stability.
**Integration:** loss functions, normalization layers.
**Verification:** unit vs. pairwise reference (≤ 2 ULP), benchmark (parallel sum ≥ 15 GFLOP/s effective).

---

## Stage 3 — Memory (`tensor/memory/`)

### 3.1 Arena Allocator
**Architecture:** bump allocator, 64-byte aligned, per-thread arenas; `FreeAll` O(1) reset.
**Technical details:** capacity doubling; allocations > 25% arena capacity bypass to system; high-water stats; debug-mode poison on reset.
**Challenges/bottlenecks:** pointer-into-arena lifetime contract; reset while views alive (debug poison detects).
**Integration:** tensor storage allocation for transient buffers.
**Verification:** benchmark (≥ 200M allocs/s); fragmentation ≤ 5%.

### 3.2 Memory Pools
**Architecture:** size-class free-list pools (16B→4KB geometric); per-CPU caches; tensor pool keyed by (dtype, shape-hash).
**Technical details:** batch refill; LIFO free for locality; autosizing (shrink/grow); hard byte cap with drain.
**Challenges/bottlenecks:** double-release detection (poison); cross-thread return merging.
**Integration:** tensor constructors (`EmptyFromPool`); autograd accumulation buffers.
**Verification:** hit rate ≥ 95%; byte-cap enforcement under storm.

### 3.3 Buffer Reuse
**Architecture:** in-place op analysis (shape/dtype match + no alias + not autograd leaf) → write-in-place; epoch-based lending registry.
**Technical details:** reuse telemetry (bytes saved, rejection reasons).
**Challenges/bottlenecks:** alias-scan cost (bounded by fan-out).
**Integration:** optimizer marks reusable buffers; executor honors plan.
**Verification:** bit-identical in-place vs. out-of-place on 200 cases; ≥ 40% allocation reduction on transformer-layer benchmark.

### 3.4 Zero-Copy Tensors
**Architecture:** `Import([]byte)` wraps external memory as tensor storage (no copy); release-callback registration; COW escalation on first write.
**Technical details:** lifetime token; `Pin/Unpin`; SHM import hook.
**Challenges/bottlenecks:** user-owned lifetime contract (mandatory release callback).
**Integration:** IPC, mmap-backed datasets, GPU staging (future).
**Verification:** callback-count test (100%); COW copies exactly once; ≥ 5 GB/s SHM round-trip.

### 3.5 Cache-Aware Allocation
**Architecture:** allocator picks alignment/size classes from detected cache topology; large tensors get page-aligned, NUMA-first-touch policy hooks.
**Technical details:** tile-size derivation from L2/L3; prefetch-friendly layout (row-major default, channel-last auto-selection).
**Challenges/bottlenecks:** topology detection portability (parse /proc or sysctl where available; defaults otherwise).
**Integration:** GEMM/conv tiling queries the same topology module.
**Verification:** L2 miss rate ≤ 5% on tiled GEMM; auto-selection ≥ 15% gain on 50% of benchmarks.

### 3.6 Memory Profiler
**Architecture:** heap/tensor profiler: live bytes, alloc rate, per-site attribution, time-series (1 Hz), OOM forensics ring buffer.
**Technical details:** `runtime.ReadMemStats` + engine allocator metrics unified; pprof-compatible export; sampled stack capture.
**Challenges/bottlenecks:** tracker self-leak prevention (pre-allocated records); overhead < 2% CPU.
**Integration:** Stage 7 runtime exports spans; CLI `astrovox profile`.
**Verification:** live-byte accounting within 1% of runtime stats; OOM dump identifies site in ≥ 90% induced cases.

---

## Stage 4 — Autograd (`autograd/`)

### 4.1 Computational Graph
**Architecture:** tape-backed dynamic graph: each op execution appends a `Node` (op-id, inputs, outputs, backward closure); edges = data dependencies.
**Technical details:** pooled node allocation; graph cap (`MaxGraphBytes`) with checkpoint-and-truncate; `GraphSnapshot()` introspection; control-flow correlation via execution ids.
**Challenges/bottlenecks:** ≤ 200 ns/op construction overhead; retained-graph memory bound.
**Integration:** ops record to tape when `GradMode` active.
**Verification:** gradient correctness on 200 random graphs (rel. error < 1e-5); overhead benchmark.

### 4.2 Reverse-Mode Autodiff
**Architecture:** reverse topological traversal of tape; chain rule per op; gradient accumulation buffers (`+=` on fan-out).
**Technical details:** `Gradients(loss, wrt...)` API; `stop_gradient` markers; deterministic accumulation order per schedule; forward-mode VJP/JVP via dual numbers (nested tape).
**Challenges/bottlenecks:** accumulation order determinism; memory for intermediates (recompute policy for order ≥ 2).
**Integration:** optimizer consumes gradients; hooks (Phase 3.5 of master roadmap) fire pre/post backward.
**Verification:** finite-difference gradient check on 500 graphs; backward ≥ 50% of forward throughput.

### 4.3 Gradient Accumulation
**Architecture:** accumulation buffers keyed by tensor identity; `Accumulate(grad)` with optional scaling; zero-init policy; buffer pooling.
**Technical details:** atomic-free (single-owner per backward pass); multi-device accumulation hook.
**Challenges/bottlenecks:** fan-out node ordering; pool pollution across steps.
**Integration:** training loop (`astrovox train`) and distributed parameter server.
**Verification:** accumulated gradient == single-batch gradient (bitwise, same thread count).

### 4.4 Custom Operators
**Architecture:** `Op` interface: `Forward(ctx, inputs) ([]*Tensor, BackwardFn)`; registration via `RegisterOp(name, factory)`.
**Technical details:** op registry with duplicate detection; custom-op shape inference hook; sandboxing hook (future); op-level profiler spans.
**Challenges/bottlenecks:** backward-fn correctness (gradcheck enforcement in tests); registration thread-safety.
**Integration:** kernel registry (Stage 5) dispatches registered ops; compiler treats custom ops as opaque nodes.
**Verification:** gradcheck (finite differences) required for every custom op in test corpus.

### 4.5 Gradient Checking
**Architecture:** automatic central-difference checker: `CheckGradients(f, x, eps)` comparing analytic vs. numeric Jacobian-vector products.
**Technical details:** adaptive eps (√machine-eps scale); random projection directions for high dims; report per-tensor rel. error.
**Challenges/bottlenecks:** non-differentiable points; numerical noise.
**Integration:** test suites for all ops; debug mode (`CheckNumerics` flag).
**Verification:** checker catches 100% of 20 seeded gradient bugs.

### 4.6 Graph Optimization
**Architecture:** post-tape passes: prune (gradient-irrelevance), fuse (elementwise backward chains), cleanup (release closures, break cycles).
**Technical details:** pruning validated by bit-identical gradients; fusion gated by deterministic flag; incremental cleanup sweeps (p99 pause < 10 ms).
**Challenges/bottlenecks:** fusion vs. accumulation-order semantics; side-effect preservation.
**Integration:** executor runs optimized backward plan.
**Verification:** pruned == unpruned bitwise on 200 graphs; ≥ 30% node reduction on dead-branch suite.

---

## Stage 5 — Kernel Registry (`kernels/`)

### 5.1 Operator Registration
**Architecture:** registry keyed by (op, dtype-set, device, arch) → kernel descriptor (factory, capabilities, cost model, determinism flag).
**Technical details:** thread-safe registration (`sync.RWMutex` + `sync.Once` per key); explicit-override flag for duplicates; immutable descriptors post-registration.
**Challenges/bottlenecks:** registration contention at init (batched during package init).
**Integration:** all kernels (Stage 2) register at init.
**Verification:** duplicate rejection test; lookup p99 < 1 µs benchmark.

### 5.2 Dynamic Dispatch
**Architecture:** query engine: (op, dtype, shape-class, device) → best kernel via specificity ranking + cost model.
**Technical details:** shape-class classification (tiny/small/medium/large/huge); autotune cache keyed by (op, shape-class, device); fallback chains (AVX2→AVX→scalar).
**Challenges/bottlenecks:** dispatch latency (function-pointer table, resolved once); autotune determinism mode.
**Integration:** ops package calls dispatch; compiler bakes selections into plan.
**Verification:** selection correctness vs. exhaustive autotune (≥ 95%); dispatch < 500 ns.

### 5.3 Backend Abstraction
**Architecture:** `Backend` interface: `Capabilities()`, `Supports(op, dtype)`, `Compile(op) (Kernel, error)`, `Device()`.
**Technical details:** global registry (`RegisterBackend`, `DefaultBackend`); CPU backend primary; capability negotiation (dtype matrix, memory budget); per-backend error taxonomy.
**Challenges/bottlenecks:** heterogeneous placement (future GPU) transfer-cost estimation.
**Integration:** compiler backend selection (Stage 6.7 of master roadmap).
**Verification:** mock-backend contract tests; capability filter accuracy 100%.

### 5.4 CPU Kernel Library
**Architecture:** library of registered CPU kernels: elementwise (SIMD-dispatched), reductions (tree), GEMM (tiled), conv (im2col), FFT (radix-2), normalization (Welford).
**Technical details:** each kernel declares vector width, alignment, memory footprint; conformance-gated promotion to default.
**Challenges/bottlenecks:** conformance runtime vs. coverage tradeoff.
**Integration:** default backend serves all ops.
**Verification:** conformance suite 100%; per-kernel benchmarks.

### 5.5 Future GPU Interface
**Architecture:** `GPUBackend` interface stub: device context, stream, event, memory import/export, kernel launch descriptor.
**Technical details:** build-tagged stubs (`cuda`, `rocm`, `vulkan`, `metal`, `webgpu`) with mock-device contract tests on CPU-only CI.
**Challenges/bottlenecks:** async error polling design; stream ordering contract.
**Integration:** backend registry accepts GPU backends when built with tags.
**Verification:** mock contract tests for 50 ops; interface compiles on all tags.

---

## Stage 6 — Compiler (`compiler/`)

### 6.1 Graph Lowering
**Architecture:** high-op → low-op decomposition (matmul→gemm+layout, conv→im2col+gemm) driven by target op-set legality table.
**Technical details:** legalization loop (rewrite until legal, complexity measure decreases); memory-op insertion from lifetime analysis; device annotations.
**Challenges/bottlenecks:** decomposition correctness; legalization termination.
**Integration:** consumes validated graph; produces executable plan for runtime.
**Verification:** equivalence on 300-program suite; lowered graph 100% backend-legal.

### 6.2 Shape Inference
**Architecture:** per-op shape rules (elementwise/broadcast, reduce/dim-drop, matmul/contracting, conv formula) with symbolic dim support.
**Technical details:** worklist propagation; join at merges; failure diagnostics naming op+dims; memoized per node.
**Challenges/bottlenecks:** termination on valid graphs (monotone lattice); sound unknown-dim propagation.
**Integration:** runs at graph build and pre-compile.
**Verification:** NumPy-equivalence on 1000 op graphs; < 50 ms on 10k nodes.

### 6.3 Type Inference
**Architecture:** dtype inference via op rules + promotion lattice; mixed-precision policy hooks.
**Technical details:** constraint solving for polymorphic ops (concat/where); join = meet of environments; precision-loss warnings.
**Challenges/bottlenecks:** soundness (never infer unsatisfied dtype).
**Integration:** compiler pipeline pass.
**Verification:** reference-type-checker agreement on 500 programs; promotion lattice 200-combination test.

### 6.4 Constant Folding
**Architecture:** lattice-based (Const/NonConst/Unknown) folding of pure ops with fixpoint iteration (≤ 4 passes).
**Technical details:** identity rules (x+0, x*1, x*0); tensor-attribute folding; constant interning; IEEE-754 exactness (no float reassociation).
**Challenges/bottlenecks:** overflow checks for int folds; NaN semantics preservation.
**Integration:** first compiler pass; feeds DCE.
**Verification:** bit-for-bit equivalence on 1000 constant subgraphs.

### 6.5 Dead Code Elimination
**Architecture:** mark-and-sweep from outputs + side-effect roots; fixpoint with other passes (≤ 10 iterations).
**Technical details:** side-effect table (I/O, RNG, stateful); control-flow DCE (dead blocks/branches).
**Challenges/bottlenecks:** observability definition completeness.
**Integration:** runs after every mutating pass.
**Verification:** 100% dead-node removal, 0 side-effect removals on adversarial suite; bit-identical outputs.

### 6.6 Operator Fusion
**Architecture:** pattern detection (elementwise chains, reduce-then-elementwise, broadcast-merge) → fused op nodes with port remapping.
**Technical details:** fusion legality (no stateful ops, no alias hazards, register-pressure estimate); fused-kernel codegen via kernel registry; fusion cache (cluster-hash → compiled).
**Challenges/bottlenecks:** float-order preservation (fast-math gate); working-set fit checks.
**Integration:** executor runs fused kernels; profiler reports fusion telemetry.
**Verification:** equivalence 100% on 500 graphs; ≥ 1.5× speedup on ≥ 70% of clusters; ≥ 30% kernel-launch reduction.

---

## Stage 7 — Runtime (`runtime/`)

### 7.1 Scheduler
**Architecture:** DAG scheduler: in-degree counters, ready sets dispatched to pool; work-conserving.
**Technical details:** lock-free per-worker deques; priority classes; batching of ready independent ops; dependency decrement atomic (exactly-once dispatch).
**Challenges/bottlenecks:** double-dispatch prevention; dispatch latency p99 < 50 µs.
**Integration:** compiler plan → scheduler; executor consumes.
**Verification:** 1M-task stress (0 double-dispatch/drop); ≥ 90% utilization at ILP ≥ 4.

### 7.2 Thread Pool
**Architecture:** fixed-size pool (default GOMAXPROCS) + dynamic autoscale variant; graceful drain shutdown.
**Technical details:** work-stealing friendly queues; panic isolation (capture, wrap, continue); affinity hooks (NUMA).
**Challenges/bottlenecks:** shutdown timeout handling (30 s default); oversubscription guard.
**Integration:** all async execution runs here.
**Verification:** ≥ 1M tasks/sec at 16 workers; 100% panic capture; drain completeness test.

### 7.3 Work Stealing
**Architecture:** Chase-Lev-style deques (mutex-guarded for stdlib purity): local push/pop, victim steal from opposite end.
**Technical details:** steal when local queue empty; randomized victim selection; steal-counter metrics.
**Challenges/bottlenecks:** steal contention under imbalance; false sharing on deque headers (cache-line padding).
**Integration:** thread pool workers.
**Verification:** load-imbalance recovery benchmark (≥ 80% efficiency at 4× skew); zero lost tasks.

### 7.4 Async Execution
**Architecture:** `Future` state machine (Pending→Completed/Failed/Cancelled); `Then` continuations; `WaitAll/WaitAny/Select`.
**Technical details:** continuation off-completion-thread by default; deadline propagation; deadlock detection (await-graph cycle check).
**Challenges/bottlenecks:** future single-use semantics; continuation ordering.
**Integration:** executor ops return futures; streaming inference pipeline.
**Verification:** 1M concurrent completions; 1000-task WaitAll semantics; deadlock detector 100% on induced cycles.

### 7.5 Cancellation
**Architecture:** token tree (parent→child propagation); cooperative checkpoints at op/iteration boundaries; forced cancel for interruptible waits.
**Technical details:** `ErrCancelled` typed error; deadline arithmetic across chains; resource-release audit on cancel.
**Challenges/bottlenecks:** leak-free cancellation (every registered resource has release path); poll frequency ≤ 10 ms.
**Integration:** all long-running ops poll tokens; CLI SIGINT wiring.
**Verification:** propagation < 5 ms on 1000-task tree; zero leaked resources in stress test.

### 7.6 Profiling
**Architecture:** runtime profiler: op-span recording (enter/exit, dispatch, wait), 100 Hz sampling, hardware-counter hooks.
**Technical details:** ring-buffer traces; per-op latency tables; Chrome-trace/pprof export; overhead governor (auto-disable beyond budget).
**Challenges/bottlenecks:** < 50 ns/op overhead when enabled, 0 when disabled.
**Integration:** executor wraps ops; `astrovox profile` consumes.
**Verification:** attribution error ≤ 5%; overhead < 5% p95.

---

## Stage 8 — Benchmark Suite
**Architecture:** benchmark taxonomy: micro (per-op), macro (pipeline), soak (duration); fixed seeds, warmup, GC control, CPU pinning hooks.
**Implementation:** `internal/benchmark` harness + `Benchmark*` funcs in every package; JSON artifacts with environment metadata; CI gate: p95 regression > 5% vs. `docs/performance-baseline.md` fails.
**Metrics:** latency (ns/op, p50/p95/p99), throughput (elements/sec, FLOP/s), memory (B/op, allocs/op), cache misses (perf-counter where available, else modeled), CPU utilization (per-worker), scalability (1/2/4/8/16 threads, efficiency curves).
**Verification:** CoV < 3% across 10 runs; ≥ 100 micro-benchmarks; full suite < 20 min.

## Stage 9 — Testing
**Architecture:** pyramid: unit ≥ 70%, integration ≥ 20%, e2e ≤ 10%.
**Implementation:**
- Unit: table-driven, hermetic (no network/clock/FS outside temp dirs), `-race` default.
- Integration: cross-module pipelines (compile→execute→backward), multi-process distributed tests, contract tests.
- Fuzz: `FuzzXxx` targets for parsers, deserializers, reshape/shape inference, config YAML; crash→regression within 24 h SLA.
- Stress: 10k-task concurrency, near-OOM, 100k-node graphs, 24 h soak with leak detection.
- Regression: golden files (checksum-verified), benchmark baselines, determinism (bit-identical across thread counts in deterministic mode).
- Property-based: internal property harness (random shape/dtype generation, invariant checking: reshape round-trip, broadcast laws, gradient finite-difference, associative reductions within tolerance).
**Verification:** coverage ≥ 85% core / ≥ 70% repo; flaky rate < 0.5%; full unit suite < 5 min.

## Stage 10 — Documentation
**Architecture:** docs-as-code: package doc comments (API docs via godoc), per-module `docs/tensor_engine/*.md` (Architecture, API, Examples, Design decisions, Performance notes, Future improvements), generated OpenAPI for service layer.
**Implementation:** this specification + per-stage docs; doc-lint (exported symbols documented); examples compile as tests; versioned docs per release.
**Verification:** 100% exported symbols documented; every example passes in CI; doc build < 2 min.

---

## Integration Strategy (End-to-End Pipeline)

```
config → logger/errors → tensor(core) → tensor/math → tensor/memory
       → kernels(registry) → graph → autograd → compiler → runtime → executor
       → profiler/benchmark (observability) → CLI/service layer
```

1. **Foundation first:** core utilities have no engine dependencies; all packages import them.
2. **Tensor core** is dependency-light (utils, errors, logger only); math layer depends on core + memory.
3. **Registry-mediated dispatch:** ops never call kernels directly — all calls route through `kernels.Dispatch`, enabling backend substitution and autotuning.
4. **Graph/autograd** consume tensors and produce tape; compiler validates/optimizes/lowers; runtime executes the plan.
5. **Observability everywhere:** profiler spans and benchmark harness are wired at op boundaries, not bolted on.
6. **Determinism contracts:** deterministic mode fixes reduction order, partitioning, and autotune selection for reproducible results.

## Risk Register
- Pure-Go SIMD limits peak FLOPs vs. assembly: mitigated by kernel-registry extension points (assembly plug-in path).
- YAML subset parser divergence: mitigated by golden-file conformance suite and JSON-first policy.
- Unsafe typed-slice views: mitigated by aliasing contract, debug poison, and view-lifetime tests.
- Windows platform quirks (atomic rename, perf counters): mitigated by fallback chains and CI matrix.
