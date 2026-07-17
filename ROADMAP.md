# ASTROVOX AI Product Roadmap

> **Status:** active delivery plan
>
> **North star:** Astrovox is an AI workspace: a trusted conversational assistant,
> a project execution environment, and an extensible operating system for AI tools.

This is an outcome roadmap, not a promise to copy another product. The intended
experience combines the clarity of a modern AI chat workspace, the visibility of
an autonomous software-work environment, and Astrovox's own memory, knowledge,
and expert-intelligence systems. Every release has measurable exit criteria;
work is only marked complete after those criteria have been met in production.

## Product principles

1. **Trust before autonomy.** The user can see what the system knows, plans,
   calls, changes, and spends; consequential actions require explicit approval.
2. **One coherent workspace.** Chat, files, research, tasks, agents, and memory
   share a project context instead of behaving as disconnected screens.
3. **Progressive disclosure.** A fast, focused chat is the default. Traces,
   terminals, citations, and agent controls appear when they are useful.
4. **Bring-your-own intelligence.** Models and tools are replaceable through
   stable provider interfaces; no UI depends on one model vendor.
5. **Secure multi-tenancy by default.** All user and workspace data is isolated
   with authorization enforced in the API and database.

## Definition of 100%

Astrovox reaches 100% only when all delivery gates below are satisfied, not when
every imaginable capability exists. A capability is done when it has a documented
user flow, authorization, observability, tests, accessible responsive UI, and a
production deployment/runbook. New capabilities enter a later roadmap cycle.

| Gate | Required evidence |
| --- | --- |
| Product | Acceptance criteria, UX states, and support ownership are documented. |
| Engineering | Typed contracts, validation, error states, unit tests, and integration coverage pass. |
| Security | Threat model reviewed; least-privilege access, audit events, and retention behavior verified. |
| Operations | Dashboards, alerts, backups, migration/rollback plan, and incident runbook exist. |
| Experience | Keyboard and screen-reader flow, mobile layout, loading/empty/error states, and performance budget pass. |

## Current baseline and first priorities

The current repository already has Supabase authentication, persisted
conversations and memory, a FastAPI intelligence router, an early knowledge
module, and a React dashboard. It does **not** yet provide a consistent design
system, streamed chat, a project domain, a durable job/agent runtime, or the
test and deployment coverage required for production claims.

The first build target is a dependable **AI Workspace Foundation**. It must ship
before autonomous agent execution, voice/video, enterprise administration, or a
large integration marketplace.

## Target user experience

### Conversation workspace (ChatGPT-quality baseline)

- A persistent left rail for projects, recent conversations, search, and a new
  conversation action; it collapses cleanly on small screens.
- A central, readable conversation surface with Markdown, syntax-highlighted
  code, tables, citations, attachments, regeneration, editing, branching, and
  stop/retry controls.
- A composer supporting text, drag-and-drop files, model/expert selection, tool
  controls, keyboard shortcuts, and clear capability/error feedback.
- A contextual right rail that shows sources, project context, saved memory,
  execution trace, and artifacts only when requested.

### Project workbench (Devin-style execution visibility)

- Each project owns its conversations, files, knowledge, memories, tasks,
  milestones, artifacts, and background work.
- An approved task can display its plan, assigned agent, live status, tool calls,
  terminal output, changed files, tests, and a review/approval checkpoint.
- Agents never receive unrestricted credentials or silently change external
  systems. Tool policies, cost limits, timeouts, and cancellation are visible.

### Research and knowledge workspace (Gemini-style organization)

- Users can create named collections, add supported sources, see ingestion
  status, search them, and inspect the passages behind every citation.
- Workspace context is explicit: users can pin, unpin, edit, export, or delete
  memories and sources at any time.

## Delivery sequence

Phases are sequential where a later phase depends on the earlier platform
contract. Within a phase, independently deployable slices may run in parallel.
Dates are intentionally omitted until the team establishes capacity, model
provider costs, and deployment constraints.

### Phase 0 — Stabilize and create the delivery baseline

**Objective:** make the present application safe to evolve.

- Adopt TypeScript for new frontend modules and introduce a shared design-token
  layer; migrate existing JavaScript incrementally without a rewrite.
- Define API request/response schemas and a versioning/deprecation policy.
- Restore a repeatable local environment with frontend and backend test commands,
  pinned tooling, pre-commit checks, and CI gates.
- Add environment validation, structured error responses, correlation IDs, and
  redacted structured logging.
- Verify Supabase schema migrations, RLS policies, backups, and a rollback path.
- Replace mojibake/incorrectly encoded UI text and centralize user-facing copy.

**Exit criteria:** clean clone can run build, lint, unit tests, and API smoke
tests; CI blocks regressions; zero secrets are tracked; authenticated API routes
have contract tests; production health/readiness checks are monitored.

### Phase 1 — AI Workspace Foundation

**Objective:** deliver the fast, polished everyday chat experience.

- Build the responsive shell: navigation rail, conversation canvas, optional
  context rail, command palette, theme support, and accessibility primitives.
- Implement conversation CRUD, title generation, search, pin/archive/delete,
  message editing, regeneration, and branching with stable IDs.
- Add server-sent streaming with cancellation, reconnect behavior, token/error
  states, persisted partial-response policy, and backpressure limits.
- Render safe Markdown, code blocks with copy/download, tables, citations, and
  sanitized links; never render model HTML unsafely.
- Add model and expert selection using an explicit capability registry, plus
  per-request latency/token/cost display when enabled by the user.

**Exit criteria:** a user can complete chat end-to-end on desktop and mobile;
stream interruption/retry works; all rendered model output is sanitized;
keyboard-only and screen-reader critical paths pass; p95 interaction metrics are
captured.

### Phase 2 — Projects, tasks, and artifacts

**Objective:** turn conversations into resumable work.

- Introduce `workspaces`, `projects`, membership, roles, tasks, milestones,
  notes, artifacts, and activity-event domain models with RLS migrations.
- Implement project home, task board, project-scoped conversations, notes, and
  artifact/file views with activity history.
- Add a durable background-job interface with idempotency keys, progress events,
  retries, cancellation, dead-letter handling, and ownership checks.
- Add project context assembly so an AI request has an explainable, bounded set
  of attached project resources.

**Exit criteria:** users can create, resume, export, and delete a project;
background work survives request loss; each project action has an audit event;
cross-workspace access is denied by tests and RLS policy verification.

### Phase 3 — Trusted knowledge and memory

**Objective:** give Astrovox durable, inspectable context.

- Complete ingestion for PDF, DOCX, PPTX, Markdown, TXT, CSV, XLSX, web pages,
  GitHub repositories, and local uploads behind a source-connector interface.
- Add malware/type/size validation, extraction sandboxing, content hashing,
  deduplication, chunking versioning, embeddings, pgvector indexes, and
  retrieval evaluation datasets.
- Ship hybrid retrieval with metadata filters, reranking, source permissions,
  grounding thresholds, and inline citations that open the exact source passage.
- Consolidate context, semantic, episodic, procedural, and workspace memory
  behind one lifecycle API: create, inspect, edit, pin, export, delete, retain,
  and synchronize.
- Add memory consent, sensitive-data detection, retention settings, and a
  retrieval trace explaining why context was used.

**Exit criteria:** ingestion is resumable and observable; answers cite retrieved
passages; unauthorized sources can never be retrieved; retrieval quality and
latency are measured against a versioned evaluation set; memory deletion is
verifiable end-to-end.

### Phase 4 — Agent orchestration and developer workbench

**Objective:** enable supervised multi-step execution.

- Define agent roles (planner, researcher, coder, tester, reviewer, memory,
  browser, file, documentation, deployment) as policy-bound capabilities, not
  hard-coded personas.
- Implement planner/executor/reviewer orchestration, a task graph, budgets,
  approval checkpoints, cancellation, resumability, and human handoff.
- Add safe tool adapters for search, browser, project files, GitHub, terminal,
  code execution, and documentation. Each adapter has schemas, permission
  checks, timeouts, rate limits, audit events, and redaction.
- Build the execution view: plan, live timeline, agent status, tool inputs and
  outputs, logs, artifacts, diffs, tests, and final review summary.
- Run code execution in isolated ephemeral environments with resource quotas and
  no ambient production secrets or unrestricted network/host access.

**Exit criteria:** agents can finish a bounded project task under a declared
budget; every tool call is attributable and reviewable; approval is required for
external writes; cancellation stops pending work; adversarial authorization and
prompt-injection tests pass.

### Phase 5 — Expert intelligence, multimodal, and automation

**Objective:** extend the workspace without fragmenting it.

- Evolve the universal router into a tested expert registry with capability
  metadata, safety notices, tool permissions, and user override controls.
- Add education, programming, research, business, creative, language, data,
  finance, cybersecurity, medical, and legal modes. High-stakes domains provide
  clear limitations, provenance, and appropriate escalation language.
- Add image understanding, OCR, screenshot/diagram/chart analysis, and
  accessible image descriptions. Add voice capture/playback with explicit consent
  and transcript review before action.
- Add user-authenticated automation schedules, triggers, run histories,
  approvals, failure notifications, and quota controls.

**Exit criteria:** every expert mode has domain evaluation cases and a safety
policy; multimodal uploads are isolated and access-controlled; automation is
idempotent, observable, pausable, and cannot bypass approval policy.

### Phase 6 — Collaboration, platform, and enterprise readiness

**Objective:** make Astrovox safe for teams and extensible for developers.

- Ship workspace invitations, granular roles, sharing links, comments,
  collaboration presence, activity feeds, and organization administration.
- Add a connector/plugin platform with OAuth credential vaulting, scopes,
  installation approval, tenant isolation, webhooks, quotas, and SDK/API docs.
- Add SSO/SAML/OIDC, SCIM, audit export, data residency/retention configuration,
  e-discovery requirements, billing/usage controls, and admin analytics.
- Build mobile-responsive and installable-web-app experience before native apps;
  build native clients only after usage data justifies them.

**Exit criteria:** permissions are tested as a matrix across every shared
resource; connector secrets are encrypted and scoped; audit logs are immutable
and exportable; SSO/SCIM and tenant offboarding have operational runbooks.

### Phase 7 — Scale, reliability, and 100% release gate

**Objective:** meet the definition of 100% for the selected product scope.

- Establish service-level objectives for availability, streaming latency,
  ingestion latency, agent completion, retrieval quality, and support response.
- Add metrics, traces, logs, synthetic checks, alert routing, on-call runbooks,
  load tests, chaos/failure drills, capacity plans, backups, and disaster
  recovery exercises.
- Perform external security review, dependency/SBOM scanning, accessibility audit,
  privacy review, penetration testing, and data-deletion verification.
- Release through staged environments, feature flags, canaries, rollback
  automation, migration safety checks, and post-release measurement.

**Exit criteria:** all Definition-of-100% gates pass; SLOs hold under load;
critical recovery drills meet objectives; no unresolved critical security issues;
the release owner signs the evidence register.

## Cross-cutting architecture decisions

| Concern | Direction |
| --- | --- |
| Frontend | React + TypeScript + Vite; reusable accessible components; server state is separate from UI state. |
| Backend | FastAPI modules split into API, application services, domain policies, and infrastructure adapters. |
| Data | PostgreSQL/Supabase for transactional data; pgvector for embeddings; Redis for cache/queues where justified. |
| Models | Provider adapter interface; capability registry; streaming and tool calls normalized behind one contract. |
| Async work | Durable job records and workers, not in-process background tasks for long-running work. |
| Security | Supabase RLS plus API authorization; no service-role key in the browser; secrets managed outside source control. |
| Observability | OpenTelemetry-compatible correlation across UI, API, jobs, tools, and model calls; redact content by default. |

## Quality and security gates for every phase

- Unit tests for domain/application logic; API integration tests for authorization
  and failure paths; browser tests for critical user journeys.
- Static checks, dependency scanning, secret scanning, formatting, and build
  checks run in CI on every pull request.
- Database migrations are forward-only, reviewed, tested on a copy of production
  data where applicable, and include rollback/mitigation instructions.
- Input limits, quotas, rate limiting, CSRF/CORS controls where relevant, secure
  headers, and content sanitization are verified for every new boundary.
- Accessibility target: WCAG 2.2 AA for the core product flows.

## Delivery cadence and decision log

Each phase starts with a one-page design decision record covering the user
problem, affected contracts, threat model, telemetry, rollout, and rollback. Each
phase ends with a demo, acceptance checklist, updated API/architecture docs, and
a measured retrospective. The roadmap is reviewed after every release using
actual adoption, quality, and cost data; sequence may change, but the gates do
not.
