# ASTROVOX AI — MISSION D-044 ARCHITECTURE

**Date:** 2026-10-16  
**Repository:** `github.com/astrovox/astrovox` (Go module, go 1.27, zero external dependencies)  
**Branch:** `main` @ `74db1493`

---

## 1. Design Principles

1. **Reuse, don't replace.** Existing working packages (tensor, autograd, model, compiler, checkpoint, inference, distributed) are reused, not rewritten.
2. **Honest capability claims.** GPU backends report `available: false`. No fake distributed workers, no fake GPU execution.
3. **Multi-process, not goroutine-parallel.** Workers are separate OS processes; coordinator and workers communicate over TCP/RPC.
4. **Fail-closed persistence.** Checkpoint writes are atomic (temp+rename), corruption is refused.
5. **Tenant-scoped everything.** Tenant identity is propagated at submission and enforced at service/storage boundaries.
6. **No fake consensus.** Coordinator is a single point of control with documented failover limitations; no custom consensus algorithm.

---

## 2. Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI / API (cmd/astrovox)                │
│  doctor · version · model inspect/validate/run              │
│  checkpoint verify · graph validate · runtime status        │
│  workflow submit · worker register · tenant-quota           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              COORDINATOR (single process)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Scheduler  │  │  Leader/Lease │  │   Authorization   │ │
│  │  (DAG +    │  │  (leases,     │  │   (tenant authz,   │ │
│  │   quotas)   │  │   heartbeats) │  │    quotas)          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Model     │  │   Artifact  │  │   Observability     │ │ │
│  │   Registry  │  │   Store     │  │   (logs, metrics)   │ │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │ TCP/RPC (versioned protocol)
┌──────────────────────▼──────────────────────────────────────┐
│              WORKER PROCESS (N instances)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Executor  │  │   Health    │  │   Resource Tracker  │ │ │
│  │  (AstroIR   │  │   (heartbeat│  │   (CPU/mem/tenant   │ │ │
│  │   engine)   │  │   /leases)  │  │    quotas)          │ │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 3. Component Responsibilities

### 3.1 Coordinator (single process)
- **Node registration:** Workers register with ID, capabilities, resource limits, tenant quotas.
- **Health monitoring:** Heartbeat-based; `healthy → suspect → unavailable → draining` transitions.
- **Membership tracking:** Active worker set, last-seen timestamps, capability index.
- **Leader election:** Single coordinator is the leader by construction; no custom consensus. Documented split-brain limitation.
- **Leases:** Task ownership leases with expiration; fencing via monotonically increasing attempt generations.
- **Task ownership:** Assigned → running → succeeded/failed/cancelled transitions persisted atomically.
- **Reassignment:** On confirmed worker failure or lease expiry, task is reassigned.
- **Stale-owner fencing:** A worker that returns after lease expiry cannot commit conflicting state.

### 3.2 Worker (separate OS process, N instances)
- **Registration:** Sends identity, capabilities, resource limits on startup.
- **Health:** Periodic heartbeats to coordinator.
- **Task execution:** Receives task, validates capability, executes via local AstroIR engine, returns result or structured failure.
- **Cancellation:** Honors context cancellation; stops execution and reports.
- **Shutdown:** Graceful; drains active tasks before exiting.

### 3.3 Scheduler (inside coordinator)
- Resource-aware: matches task requirements to worker capabilities (CPU, memory, ops, model).
- Bounded pending queue with explicit backpressure (queue-full refusal).
- Deadline-aware dispatch.
- Per-tenant fairness and quota enforcement.
- Starvation prevention: aging/priority boost for long-waiting tasks.

### 3.4 Persistence Layer
- **Checkpoint format** (`internal/checkpoint/`): versioned, CRC64, atomic temp+fsync+rename.
- **Workflow state** (`internal/workflow/`): task state snapshots persisted as JSON.
- **Artifact store:** content-addressed (planned; file-based for MVP).
- **Model registry:** versioned model artifacts with validation before activation.

## 4. Execution Contract (D-044 Phase 1)

Every execution request carries:

| Field | Purpose |
| --- | --- |
| Protocol version | Compatibility check; unknown versions refused |
| Task ID | Unique; idempotency key |
| Tenant ID | Authorized identity (not client-trusted) |
| Model/artifact ID | Version-pinned; validated before execution |
| Operation spec | What to execute; validated against backend capabilities |
| Resource requirements | CPU, memory, queue depth checks |
| Deadline | Enforced at admission and during execution |
| Cancellation ID | Propagated to worker; context cancellation |
| Idempotency key | Prevents duplicate side effects |
| Trace ID | End-to-end tracing |

Every execution response carries:

| Field | Purpose |
| --- | --- |
| Task ID | Echo of request |
| State | `queued/assigned/running/succeeded/failed/cancelled` |
| Attempt | Monotonically increasing generation |
| Output or structured error | Typed error codes only |
| Timestamp | Monotonic clock (not wall-clock for ordering) |

## 5. What Is NOT Built (deferred with reasons)

| Subsystem | Reason |
| --- | --- |
| Custom consensus algorithm | Coordinator is single-leader by design; documented split-brain limitation. No production consensus without rigorous review. |
| GPU acceleration | All GPU backends report `available: false`; no hardware in this environment. |
| Live provider credentials | No credentials available; mock providers used for contract tests. |
| Multi-tenant isolation | No tenant identity in Go core; to be built in Stage 8. |
| Workflow recovery after node restart | Workflow engine exists (D-042) but distributed restart recovery not yet integrated. |

---

## 6. Key Design Decisions (ADRs)

### ADR-1: Single-coordinator, no custom consensus
**Decision:** The coordinator is the single leader by construction. No Raft/Paxos implementation.
**Rationale:** D-044 rules prohibit claiming fault-tolerant consensus without rigorous design. A single coordinator with documented failover limitations is honest and verifiable.

### ADR-2: Process-separated workers, not goroutines
**Decision:** Workers are separate OS processes communicating over TCP/RPC.
**Rationale:** Goroutines are not a security or failure boundary. Real process separation is required for honest fault isolation and distributed semantics.

### ADR-3: Reuse `internal/distributed/` primitives
**Decision:** Build coordinator/worker on top of existing `ProcessGroup`, `TCPStore`, `RPCManager` rather than inventing a new transport.
**Rationale:** These packages are tested and real; reusing them avoids duplicate abstractions.

### ADR-4: Tenant identity propagated at submission
**Decision:** Tenant ID is part of every execution request and validated against authenticated identity, not trusted from the client.
**Rationale:** D-044 rules prohibit trusting client-supplied tenant IDs.
