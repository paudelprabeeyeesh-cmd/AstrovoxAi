# Research Notes — Operating Systems

> Implementation anchors: `internal/runtime` (scheduler, allocator),
> `internal/memory` (arena/slab/pool allocators).

## 1. Scheduler

Astrovox's task scheduler adapts the classic CFS intuition of *virtual runtime*
to GPU workloads. Rather than per-task time slices, each task carries a priority
class (`runtime/priority.go`) and a cost estimate derived from op FLOPs. The
work-stealing deque (`internal/runtime/workstealing.go`, Chase–Lev) keeps hot
cores busy without a shared run queue.

| OS concept | Astrovox analogue |
|---|---|
| Run queue per CPU | Per-worker deque + steal |
| Preemption | Batch-boundary checks |
| Nice / priority | Explicit `Priority` classes |
| cgroup limits | `ResourceLimits` in `internal/sandbox` |

### Fairness

Fairness is enforced by an aging factor: a task's effective priority rises with
the time since it was first enqueued, so urgent short jobs cannot starve long
GEMMs.

## 2. Memory Management

| OS concept | Astrovox analogue |
|---|---|
| Buddy allocator | `internal/memory/buddy.go` |
| Slab allocator | `internal/memory/slab.go` |
| Arena / region | `internal/memory/arena.go` |
| `mmap`/`munmap` | `memory.Alloc`/`memory.Free` with alignment |
| NUMA policy | `internal/runtime/numa.go` |

Tensor lifetimes are graph-shaped, not process-shaped, so the allocator favours
bump-pointer allocation within an arena and bulk release at microbatch end. This
is the same trade-off a kernel makes allocating page frames for a short-lived
process.

## 3. What Astrovox Deliberately Does Not Do

- No demand paging: device memory is allocated eagerly and never swapped.
- No copy-on-write fork: tensors are immutable within a graph.
- No syscall boundary: the "user" of the allocator is trusted Go code inside the
  sandbox's capability model.
