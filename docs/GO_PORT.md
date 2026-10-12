# Go Backend: Port Progress

The Python backend (`02-Backend/app`) holds 1,509 files / ~225,400 lines
across 88 packages. Most of that is speculative — `quantum/`,
`philosophical_cognition/`, `omniscient_ai/`, `multiverse/`,
`neural_architectures/`, `futuristic_interfaces/` — and the task register's
own guidance (D01-10, D01-11) is to inventory it, classify each piece as
live, tested-but-unused, or dead, and cut. A mechanical rewrite of 225k
lines would reproduce the sprawl in a different language, which is the
exact mistake the register warns about.

So this document records what has been ported, what has not, and why.
The decision is the port of the **product surface**, not of the file tree.

## Ported to Go

| Domain | Package | Tests |
|---|---|---|
| HTTP boundary: router, envelope, middleware chain, bounded ids | `internal/httpapi` | 33 |
| API server: auth, chat, conversations, memory, retrieval, tools, health | `cmd/api` | 21 |
| Config: fail-fast validation of every secret | `internal/api/config` | 13 |
| Structured logging with closed-key redaction | `internal/api/logging` | 13 |
| Prometheus metrics with bounded route labels | `internal/api/metrics` | 14 |
| Request correlation: sanitised ids, bounded spans | `internal/api/tracing` | 18 |
| CORS, body limits, recovery, client IP | `internal/api/middleware` | 16 |
| Idempotency for mutating requests | `internal/api/idempotency` | 11 |
| SSRF guard (resolves before it allows) | `internal/api/ssrf` | 12 |
| Web fetch tool | `internal/api/webfetch` | 9 |
| Chat orchestrator with the spend gate first | `internal/chat` | 15 |
| Conversations with branching and tenant scoping | `internal/conversations` | 14 |
| Explicit memory with the deny list | `internal/memstore` | 19 |
| Retrieval with the owner inside the search key | `internal/retrieval` | 21 |
| Tool registry, validated args, budgets | `internal/tools` | 20 |
| Agent loop with hard caps | `internal/tools/agent` | 15 |
| JWT, OAuth server, RBAC | `internal/auth` | (pre-existing) |
| Knowledge graph | `internal/knowledge` | (pre-existing) |

The Go API is a runnable service: `config.Load()` refuses to start on a
placeholder secret, every subsystem mounts behind one auth chain, and the
spend gate runs before the provider call.

## Deliberately not ported

| Python package | Why |
|---|---|
| `quantum/`, `philosophical_cognition/`, `omniscient_ai/`, `multiverse/`, `neural_architectures/`, `futuristic_interfaces/`, `acdos/`, `agi_reasoning/` | Research scaffolding with no interface to the product path. 225k lines of this is not engineering, it is inventory. |
| `billing/`, `stripe_webhooks` | Needs Stripe test mode. Porting against a fake would produce a fake billing system, which is worse than none. |
| `supabase/`, `database/` | The durable store is a schema decision. The Go backend uses in-process stores and says so. |
| `audio/`, `video/`, `multimodal/` | Needs provider credentials and hardware. |
| `fine_tune/`, `training/` | Needs GPUs. |
| `self_evolution/`, `self_improvement/` | Not a product feature. |
| The remaining 60+ service packages | Each needs its own real-world dependency (a Zuora API, a Kafka cluster, an SMTP relay). Porting them now moves bugs between languages rather than removing them. |

## The remaining Python surface that matters

The Python backend still serves: Stripe billing, SMTP delivery, Supabase
persistence, provider adapters with recorded fixtures, and the
observability exporters. Those are the parts with real credentials
attached. The Go API runs beside them rather than replacing them.

## Next

1. Register `web.fetch` on the Go tool registry, so an agent can call it.
2. Port the email token delivery (already written once, in
   `app/services/token_mailer.py`) to Go, so the Go server can issue
   verification emails.
3. Port the Supabase schema the Python side depends on into the migrations
   directory as the authoritative source, so one path owns the schema
   (D14-02).
4. Cut the speculative packages from the Python side, or move them under
   `experiments/` (D01-11).
