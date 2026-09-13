# Intelligence Kernel Architecture (Stage 31)

The Distributed Multimodal Intelligence Engine (DMIE) is the central
execution layer of AstrovoxAI. Every request flowing through the platform
ultimately passes through `app.kernel`.

## Components

| Module | Responsibility |
|--------|----------------|
| `kernel/bus.py` | Global event bus (pub/sub) |
| `kernel/artifacts.py` | Universal artifact system with lineage |
| `kernel/context.py` | Token-budgeted context engine |
| `kernel/router.py` | Cost- and capability-aware model router |
| `kernel/scheduler.py` | DAG-based workflow scheduler |
| `kernel/agents.py` | Autonomous agent runtime |
| `kernel/cost.py` | Per-workspace quotas and cost tracking |
| `kernel/evaluation.py` | Per-response evaluation records |
| `kernel/observability.py` | Tracing, metrics, SLO tracking |
| `kernel/__init__.py` | `IntelligenceKernel` facade |
| `kernel/api.py` | FastAPI surface (24 routes) |

## Request Lifecycle

1. Caller submits a `KernelRequest` to `IntelligenceKernel.handle`.
2. `ContextEngine` deduplicates, ranks, and token-budgets blocks from
   every registered source (system, history, memory, retrieval, tools,
   preferences).
3. `ModelRouter` picks a primary model + fallback chain based on
   policy (cost, latency, quality, capability, tier).
4. The chosen model handler runs; on failure the router advances to
   the next fallback.
5. The result is registered as an `Artifact`, cost is recorded against
   the workspace, an `Evaluation` is appended, and a `Span` is closed.
6. An event is published to the bus so observability, agents, and
   downstream services can react.

## Event Topics

| Topic | Producer | Consumer |
|-------|----------|----------|
| `artifact.registered` | `artifacts.py` | catalog, marketplace |
| `context.built` | `context.py` | observability |
| `model.invocation` | `router.py` | cost, evals |
| `workflow.job.started` | `scheduler.py` | dashboard |
| `workflow.job.succeeded` / `failed` | `scheduler.py` | monitoring |
| `agent.finished` | `agents.py` | workflows, UI |
| `kernel.handled` / `failed` | `__init__.py` | observability |

## Cross-Cutting Concerns

- **Cost control** — every request records tokens + cost against the
  workspace quota; routers can be told the user tier so public-tier
  users never see premium models.
- **SLOs** — defaults track p95 latency, error rate, and retrieval
  precision; `SLOTracker.compliance()` is the source of truth.
- **Tracing** — every kernel request opens a span; downstream jobs
  inherit the `request_id` for correlation.
- **Lineage** — `Artifact.derive` records parent + provenance so we
  can trace the chain from a final response back to source inputs.

## API Surface (24 routes under `/kernel`)

- `POST /kernel/handle` — end-to-end request orchestration.
- `GET  /kernel/status` — aggregated system health.
- `GET  /kernel/events` — bus tail.
- `GET  /kernel/models` / `POST /kernel/models/select` — model catalog + routing.
- `POST /kernel/artifacts` / `GET /kernel/artifacts` / `GET /kernel/artifacts/{id}` — artifact management.
- `POST /kernel/workflows/run` / `approve/{id}` / `cancel/{id}` — DAGs.
- `POST /kernel/agents` / `GET /kernel/agents` / `POST /kernel/agents/run` — agents.
- `POST /kernel/quotas/{id}` / `GET /kernel/quotas/{id}` / `GET /kernel/costs` — cost.
- `GET  /kernel/evaluations` / `summary` — evals.
- `POST /kernel/slo` / `GET /kernel/slo` / `/metrics` / `/traces` — observability.
- `POST /kernel/context/build` — context composition.

## Migration Strategy

Existing modules continue to work as-is. New capabilities should:

1. Subscribe to kernel events instead of importing modules directly.
2. Register artifacts instead of returning raw dicts when the output
   may be referenced by other components.
3. Surface cost & evaluation through the kernel so dashboards and
   rate limiters stay accurate.

Backward compatibility is preserved by keeping the legacy routers
(`/auth/*`, `/chat/*`, etc.) untouched.