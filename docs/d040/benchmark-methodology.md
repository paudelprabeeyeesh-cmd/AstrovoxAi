# D-040 Benchmark Methodology

Machine: 11th Gen Intel Core i5-1135G7 @ 2.40GHz (8 logical CPUs),
Windows, Go 1.27.1 (go1.27.1), CGO disabled, `go test -bench` with
`-benchtime` as noted. Numbers below are from this session's actual runs
and are NOT production capacity predictions.

## Method

`go test -run XXX -bench . -benchtime 50x ./model/ ./inference/ ./tensor/math/`

## Results (model + inference; 50 iterations each)

| Benchmark | ns/op | B/op | allocs/op |
| --- | --- | --- | --- |
| LinearForward (8x64 @ 64x32) | 30,592 | 5,544 | 26 |
| MLPForward (8x64 ->128->64->10, relu) | 351,398 | 47,688 | 92 |
| MSELoss (16x32 -> 8) | 8,228 | 4,832 | 63 |
| Checkpoint save (32-64-32 MLP) | 12,192,048 | 156,809 | 33 |
| Checkpoint load (same file) | 4,747,456 | 76,623 | 27 |
| Checkpoint restore-into-model | 110,318 | 84,417 | 51 |
| ExecutorThroughput (1 request, 4 workers) | 38,495 | 3,734 | 71 |
| ExecutorQueueLatency (4 concurrent, 2 workers) | 34,004 | 15,431 | 290 |

## Reading these numbers honestly

- Checkpoint save/load are dominated by filesystem latency (fsync), not
  CPU: the 12ms save includes an fsync per write. That is the durability
  cost, and it is the intended trade.
- Executor throughput includes goroutine hand-off, context handling, and
  stats locking on top of a ~35us MLP forward; the marginal scheduling
  overhead is small relative to model execution at this size.
- All allocations are bounded per request; no per-request goroutine is
  created beyond the pool's workers (futures do not spawn goroutines).
- Tensor/math benchmarks (GEMM sizes, conv sizes) run under
  `tensor/math/bench_test.go`; use `go test -benchmem ./tensor/math/` and
  compare against the naive references by swapping the kernel, not by
  trusting the number.

## Not measured

- CPU/memory profiles were not captured in this session (documented
  limitation).
- No sustained-load or long-run soak tests were executed.
