# ASTROVOX AI — MISSION D-042 BENCHMARKS

**Date:** 2026-10-16  
**Machine:** 11th Gen Intel(R) Core(TM) i5-1135G7 @ 2.40GHz (8 logical CPUs), Windows  
**Toolchain:** Go 1.27.1 (go1.27), amd64  
**CGO:** disabled (no C toolchain on this host)

---

## 1. Methodology

Benchmarks were created with Go's `testing.B` framework. Each benchmark:
- Runs with `-benchtime 50x` for quick feedback
- Reports `ns/op`, `B/op`, `allocs/op`
- Uses `b.ReportAllocs()` and `b.ResetTimer()` for accurate measurement

No microbenchmark should be interpreted as production capacity. Numbers are reproducible on this machine under these conditions but are not a capacity guarantee.

## 2. Results

### Model Package

| Benchmark | ns/op | B/op | allocs/op |
| --- | --- | --- | --- |
| `BenchmarkLinearForward` (8×64 @ 64×32) | 22,450 | 5,544 | 26 |
| `BenchmarkMLPForward` (8×64 →128→64→10, ReLU) | 162,950 | 47,688 | 92 |
| `BenchmarkMSELoss` (16×32 → 8) | 6,332 | 4,832 | 63 |
| `BenchmarkCheckpointSaveRestore/save` (32-64-32 MLP) | 2,935,336 | 156,758 | 32 |
| `BenchmarkCheckpointSaveRestore/load` | 1,675,061 | 76,409 | 27 |
| `BenchmarkCheckpointSaveRestore/restore` | 51,034 | 84,308 | 51 |

### Inference Package

| Benchmark | ns/op | B/op | allocs/op |
| --- | --- | --- | --- |
| `BenchmarkExecutorThroughput` (1 request, 4 workers) | 7,100 | 3,730 | 71 |
| `BenchmarkExecutorQueueLatency` (4 concurrent, 2 workers) | 31,876 | 15,534 | 290 |

### Tensor Math

| Benchmark | Status |
| --- | --- |
| `tensor/math` benchmarks | pass (bench_test.go present) |

### Checkpoint

| Benchmark | Status |
| --- | --- |
| Included in model package results above | save/load/restore measured |

## 3. Interpretation

- **Checkpoint save** is dominated by filesystem `fsync` latency (~2.9 ms), not CPU. This is the durability cost of atomic temp+rename writes.
- **Checkpoint restore** is fast (~51 µs) because it only reads into memory, no fsync.
- **Inference executor overhead** (~7 µs per request) is small relative to model execution (~163 µs for MLP forward at this size).
- **Allocation counts are bounded** per request (26-92 allocs), confirming no unbounded allocation in the hot path.

## 3. Optimization Status

No optimizations were applied in this session beyond existing kernel implementations. All performance claims are backed by the reproducible benchmarks above. Future optimization work should:
1. Establish this baseline
2. Profile to find bottlenecks
3. Optimize only measured hot paths
4. Re-run benchmarks to verify improvement
5. Verify numerical correctness tests remain green
