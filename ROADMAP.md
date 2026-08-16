# Astrovox AI Technical Roadmap

> **Status:** active delivery plan
>
> **North star:** Astrovox is an AI workspace platform, not just a chatbot. It should combine premium chat, project execution, memory, retrieval, agents, multimodal input, and enterprise controls into one coherent product.

This roadmap is written for engineering execution. It prioritizes the foundational platform layers that make every later feature safer, cheaper, and faster to ship.

## Product strategy

Astrovox should win by being:

- a trusted assistant for everyday chat and writing,
- a project workspace for ongoing work,
- a knowledge system with inspectable citations and memory,
- an execution environment for supervised agent workflows,
- and a platform that can expand into many domains without rewriting the core.

The goal is not to ship every AI feature immediately. The goal is to build a platform that can support many fields while staying maintainable, secure, and measurable.

## What "best AI platform" means here

To reach a world-class standard, Astrovox needs all of the following:

- premium conversational UX with streaming, editing, branching, citations, and artifacts,
- project/workspace persistence with tasks, files, notes, and history,
- secure retrieval and memory with permissions and source traceability,
- model routing and fallback across multiple providers,
- safe agent orchestration with approvals, logging, and budgets,
- multimodal support for documents, images, screenshots, OCR, and voice,
- team and enterprise controls such as RBAC, audit logs, SSO, and quotas,
- observability, evaluations, and release gates so quality can be measured.

## Roadmap principles

1. Trust before autonomy.
2. One workspace, not many disconnected tools.
3. Every important action must be observable.
4. Every expensive action must be budgeted.
5. Every protected resource must be authorized.
6. New capabilities must be built on reusable platform primitives.

## Definition of done

A feature is only considered complete when it has:

- a documented user flow,
- validated API contracts,
- authorization rules,
- error states and loading states,
- tests,
- telemetry,
- and a production rollout plan.

## Roadmap phases

### Phase 0 - Platform stabilization

Objective: make the current application safe to evolve.

Deliverables:

- consistent codebase structure and naming,
- environment validation,
- typed frontend work for new components,
- backend request validation and error handling,
- structured logs and correlation IDs,
- build/test automation,
- database migration discipline,
- security headers and rate limiting,
- documentation cleanup.

Exit criteria:

- clean local build,
- passing backend tests,
- passing frontend build,
- no secrets committed,
- authenticated routes have authorization coverage.

### Phase 1 - Premium chat foundation

Objective: deliver a ChatGPT-class chat experience.

Deliverables:

- responsive shell with left rail, conversation canvas, and right context rail,
- message streaming with cancel/retry/regenerate,
- markdown, tables, code highlighting, copy actions, and sanitized links,
- conversation history, title generation, search, pin/archive/delete,
- message edit and branch support,
- attachment upload and safe file previews,
- keyboard shortcuts and accessible empty/error/loading states,
- mobile-friendly layout.

Exit criteria:

- a user can complete a full chat session on desktop and mobile,
- streamed responses are reliable,
- content rendering is safe,
- keyboard-only navigation works for the main flow.

### Phase 2 - Workspace and projects

Objective: turn chat into persistent work.

Deliverables:

- workspaces, projects, roles, membership, and invitations,
- project-scoped conversations and files,
- tasks, milestones, notes, and artifacts,
- activity feed and change history,
- resumable project sessions,
- project-level search and filtering,
- saved context attached to each project.

Exit criteria:

- a user can create, resume, and export a project,
- workspace isolation is enforced,
- shared resources have audit trails.

### Phase 3 - Knowledge and memory

Objective: make Astrovox useful for long-term work.

Deliverables:

- document ingestion for PDF, DOCX, PPTX, Markdown, TXT, CSV, XLSX, web pages, GitHub repositories, and local files,
- OCR and image text extraction,
- chunking, embeddings, metadata, deduplication, and versioning,
- hybrid retrieval with filters, ranking, and citations,
- memory types for semantic, episodic, workspace, and procedural context,
- memory editing, export, deletion, and retention controls,
- retrieval traces explaining why a passage was used.

Exit criteria:

- answers cite the exact sources used,
- unauthorized content cannot be retrieved,
- memory edits and deletes are reflected end to end,
- retrieval quality is measured against a test set.

### Phase 4 - Model platform

Objective: make model usage flexible and cost-aware.

Deliverables:

- model gateway for OpenAI, Anthropic, Gemini, and open-source providers,
- capability registry for context window, streaming, tools, and safety,
- routing by quality, latency, privacy, cost, and availability,
- fallback behavior and provider health tracking,
- prompt/version management,
- usage accounting and per-workspace budgets,
- evaluations for response quality and tool behavior.

Exit criteria:

- models can be swapped without changing the UI contract,
- requests are routed intentionally,
- costs are visible and bounded,
- regressions can be detected with evals.

### Phase 5 - Agent execution

Objective: add supervised automation without losing control.

Deliverables:

- planner, executor, reviewer, memory, research, browser, file, and testing roles,
- task graphs, approvals, retries, cancellation, and resumability,
- terminal and code execution in isolated sandboxes,
- GitHub and deployment adapters with least-privilege permissions,
- tool-call logging and redaction,
- human approval gates for risky or external actions,
- final execution summaries with diffs and tests.

Exit criteria:

- a task can be planned, executed, and reviewed with a full audit trail,
- dangerous actions require approval,
- no tool has unrestricted host or network access.

### Phase 6 - Multimodal and voice

Objective: support richer inputs and outputs.

Deliverables:

- screenshot analysis,
- OCR,
- diagram, chart, and image understanding,
- voice input and text-to-speech,
- real-time conversation workflows,
- transcript review before side effects,
- explicit consent for microphone and camera use.

Exit criteria:

- multimodal uploads are isolated and traceable,
- voice flows are understandable and reviewable,
- accessibility is preserved.

### Phase 7 - Collaboration and enterprise

Objective: make Astrovox ready for teams.

Deliverables:

- organizations, shared workspaces, and granular roles,
- comments, mentions, sharing, and presence,
- SSO/SAML/OIDC and SCIM,
- audit logs and export,
- retention, deletion, and compliance controls,
- billing, quotas, usage analytics, and admin dashboards,
- connector and plugin platform with approval and isolation,
- team onboarding and admin workflows.

Exit criteria:

- permissions are tested across all shared resources,
- tenant boundaries are enforced,
- admin and audit flows are operational,
- enterprise onboarding is supportable.

### Phase 8 - Reliability and scale

Objective: make the platform dependable at growth scale.

Deliverables:

- CI/CD and release automation,
- metrics, logs, traces, and alerting,
- load testing and resilience drills,
- backup and restore validation,
- disaster recovery plan,
- security scanning and dependency hygiene,
- accessibility audits,
- cost monitoring and capacity planning.

Exit criteria:

- the platform has measured SLOs,
- rollback is safe,
- incidents are diagnosable,
- production releases are low risk.

## Vertical AI roadmap

Astrovox should support specialized modes, but only after the core platform is stable. These modes share the same model gateway, memory, retrieval, project, and agent systems.

### Low-risk general-purpose modes first

- Programming AI
- Research AI
- Business AI
- Education AI
- Creative AI
- Language AI

### High-risk domains later, with extra controls

- Medical AI
- Legal AI
- Finance and trading AI
- Cybersecurity AI

Each high-risk mode must include:

- explicit limitations,
- source citations,
- confidence or uncertainty indicators,
- escalation language,
- safety tests,
- and domain-specific review rules.

## Recommended build order for the next 90 days

1. Finish the premium chat shell and streaming behavior.
2. Add workspace/project models and permissions.
3. Complete secure upload plus cited retrieval.
4. Add agent task execution with approvals and audit logs.
5. Add model routing, evaluations, observability, and cost controls.
6. Add one strong vertical use case and recruit design partners around it.

## What not to do yet

Do not try to ship all of these at once:

- native mobile apps,
- voice,
- vision,
- plugins,
- every enterprise integration,
- every high-risk vertical,
- or fully autonomous agents without approvals.

The product becomes valuable by being exceptional in one workflow first, then expanding carefully.

## Cross-cutting engineering decisions

| Area | Direction |
| --- | --- |
| Frontend | React, TypeScript, Vite, accessible component system, responsive shell |
| Backend | FastAPI with clear application, domain, and infrastructure layers |
| Database | PostgreSQL/Supabase for transactional data, pgvector for embeddings |
| Cache / jobs | Redis where queues or caching are truly needed |
| Models | Provider adapters behind a stable model contract |
| Security | JWT validation, RLS, audit logging, least privilege, secret hygiene |
| Observability | Structured logs, traces, metrics, and request correlation |
| Testing | Unit, integration, and user-flow tests for every shipped feature |

## Release gates

Every phase should end with:

- an implementation demo,
- test evidence,
- updated docs,
- security review notes,
- and a rollback plan.

## Final note

Astrovox reaches "best in class" by being reliable, understandable, and extendable. That means every new feature must make the platform more useful without making it harder to trust or operate.
