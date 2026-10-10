# Research Notes — Linux Kernel

> Implementation anchor: `internal/runtime`, `internal/kernel`,
> `internal/backend/cpu.go`.

## 1. Scheduling Equivalents

| Linux | Astrovox |
|---|---|
| `SCHED_NORMAL` CFS | work-stealing deque with priority classes |
| `SCHED_FIFO` real-time | `PriorityUrgent` tasks bypass the deque |
| `kthread` workers | `internal/runtime` worker pool |
| `preempt_count` | batch-boundary cancellation checks |
| `smp_barrier` | `ProcessGroup.Barrier` |
| softirq deferral | deferred completion callbacks in `async.go` |
| RCU read side | epoch-guarded read locks on the KV cache |

## 2. Memory Equivalents

| Linux | Astrovox |
|---|---|
| `alloc_pages` | `internal/runtime/numa.go` pool |
| SLUB | `internal/memory/slab.go` size classes |
| `dma_alloc_coherent` | unified-memory buffers in `backend/metal_directml.go` |
| `get_user_pages` | tensor views with stride metadata |
| OOM killer | `sandbox.Environment.Allocate` violation errors |
| `/proc/meminfo` | `memviz` tracker + report |

## 3. Process Model

The closest analogue to a process is a **sandbox**: `internal/sandbox` gives a
task its own capability set and resource limits, and isolates panics — the same
boundary a kernel draws between tasks, minus the MMU.

## 4. What Is Different

Astrovox never syscalls into device memory: kernels are JIT-invoked in-process
and the "driver" is a function pointer. This keeps dispatch at ~100 ns instead
of the microsecond range a real kernel-to-GPU round trip costs, at the price of
no isolation between engine and device driver.