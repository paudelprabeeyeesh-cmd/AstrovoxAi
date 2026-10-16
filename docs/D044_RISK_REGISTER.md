# ASTROVOX AI — MISSION D-044 RISK REGISTER

**Date:** 2026-10-16  
**Repository:** `github.com/astrovox/astrovox`  
**Branch:** `main` @ `74db1493`

---

## Risk Classification

| Severity | Meaning |
| --- | --- |
| **High** | Blocks production correctness or security; must be resolved before distributed deployment. |
| **Medium** | Degrades reliability or security; mitigations required but not blocking initial implementation. |
| **Low** | Cosmetic or edge-case; document and monitor. |

---

## 1. High Risks

### R-01: No race detector available
**Severity:** High  
**Detail:** `go test -race` requires cgo and a C compiler (`gcc`), which is not installed on this Windows host. All concurrency tests (workflow engine, scheduler, inference executor) pass uninstrumented. Race conditions in distributed coordination cannot be verified locally.  
**Mitigation:** Document the limitation explicitly; run `go test -race` on a CI runner with a working C toolchain; use deterministic synchronization and bounded concurrency in all new code.  
**Status:** Open — environment limitation.

### R-02: No multi-tenancy in Go core
**Severity:** High  
**Detail:** No tenant identity, tenant-scoped authorization, or per-tenant quotas exist in the Go codebase. Any distributed deployment would have no cross-tenant isolation boundary.  
**Mitigation:** Build tenant identity propagation and authorization checks in Stage 8 before any multi-user deployment.  
**Status:** Open — to be implemented in Stage 8.

### R-03: No coordinator/worker process mode
**Severity:** High  
**Detail:** `internal/controlplane/` does not exist. `internal/distributed/` has `ProcessGroup`/`TCPStore`/`RPCManager` primitives but no coordinator service, no worker process, no deployment topology.  
**Mitigation:** Build coordinator and worker as separate OS processes in Stage 2, using existing `internal/distributed/` primitives.  
**Status:** Open — to be implemented in Stages 1–2.

### R-04: GPU backends are simulation stubs
**Severity:** High (if claimed as real) / Low (if honestly labeled)  
**Detail:** CUDA/Vulkan/Metal/WebGPU/ROCm backends all report `available: false` and device names contain "Simulated". `CUDA.available = false`. No hardware verification possible.  
**Mitigation:** Never claim GPU acceleration. Document CPU as the only verified backend.  
**Status:** Documented — honest labeling.

---

## 2. Medium Risks

### R-05: Provider gateway is mock-only
**Severity:** Medium  
**Detail:** Providers use recorded responses (`f4845c35 feat(providers): recorded responses so CI never needs live keys`). No live provider integration.  
**Mitigation:** Use deterministic mock providers for contract tests; clearly distinguish mock from live; require a real successful integration test before claiming any provider capability.  
**Status:** Open — to be addressed in Stage 17.

### R-06: No metrics exporter / histograms
**Severity:** Medium  
**Detail:** Counters exist but no export/push mechanism; no histograms for latency distributions.  
**Mitigation:** Build observability plane in Stage 19 with bounded metric labels and secret redaction.  
**Status:** Open — to be implemented in Stage 19.

### R-07: Workflow engine not yet integrated with distributed execution
**Severity:** Medium  
**Detail:** `internal/workflow/` exists (D-042 session) with DAG tasks, retries, cancellation, idempotency, file persistence — but it has not been integrated with the coordinator/worker or tested across process restart.  
**Mitigation:** Integrate workflow engine with distributed execution in Stage 18; add kill/restart recovery test.  
**Status:** Open — to be implemented in Stage 18.

### R-08: No model artifact store / artifact integrity
**Severity:** Medium  
**Detail:** Checkpoints exist (versioned, CRC64, atomic), but there is no content-addressed artifact store with cryptographic hashes for model files and workflow outputs.  
**Mitigation:** Build artifact store in Stage 12.  
**Status:** Open — to be implemented in Stage 12.

### R-09: No secret handling infrastructure
**Severity:** Medium  
**Detail:** No secret store, environment variable handling, or redaction pipeline beyond basic ad-hoc handling.  
**Mitigation:** Use environment variables or documented secret-provider interface; redact secrets from logs (D-041 already does this in tools package).  
**Status:** Open — to be addressed in Stages 8/17.

---

## 3. Low Risks

### R-10: CLI subcommands may be stubs
**Severity:** Low  
**Detail:** `cmd/astrovox/` has subcommand dispatch (init, build, train, infer, benchmark, profile, graph, docs, plugin, doctor, export) but some may be thin.  
**Mitigation:** Verify each advertised command works; implement missing ones in Stage 19.  
**Status:** Partial — to be verified/completed in Stage 19.

### R-11: No CI workflow verification
**Severity:** Low  
**Detail:** CI workflows may exist but have not been executed in this environment.  
**Mitigation:** Review and run CI workflows in Stage 22.  
**Status:** Open — to be verified in Stage 22.

---

## 8. Risk Register Summary Table

| ID | Risk | Severity | Status | Target Stage |
| --- | --- | --- | --- | --- |
| R-01 | No race detector | High | Open | Stage 22 (CI) |
| R-02 | No multi-tenancy | High | Open | Stage 8 |
| R-03 | No coordinator/worker | High | Open | Stages 1–2 |
| R-04 | GPU stubs | High (if claimed) | Documented | N/A — honest labeling |
| R-05 | Mock providers | Medium | Open | Stage 17 |
| R-06 | No metrics exporter | Medium | Open | Stage 19 |
| R-07 | Workflow not distributed | Medium | Open | Stage 18 |
| R-08 | No artifact store | Medium | Open | Stage 12 |
| R-09 | No secrets infrastructure | Medium | Open | Stages 8/17 |
| R-10 | CLI stubs | Low | Partial | Stage 19 |
| R-11 | CI not verified | Low | Open | Stage 22 |

**Acceptance rule:** No high-severity risk may remain unresolved at mission completion without a documented, explicit acceptance of the risk.
