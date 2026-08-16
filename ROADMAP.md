# Astravox AI Product and Technical Roadmap

> **Status:** active delivery plan
>
> **North star:** Astravox AI is an AI operating system where people and teams can think, research, build, automate, and retain knowledge in one trusted workspace.

This is an execution roadmap, not a list of claims. A capability is only released after it passes its product, security, reliability, and rollout gates.

## Product thesis

Astravox AI combines five capabilities that are usually separate:

1. A fast, delightful conversational interface.
2. Persistent projects, files, tasks, and organizational knowledge.
3. A multi-model intelligence layer optimized for quality, latency, privacy, and cost.
4. Supervised agents that execute work with clear boundaries and human approval.
5. Enterprise governance that makes real business data safe to use.

The first product wedge should be the **AI development and research workspace**. Users should be able to reason in chat, attach evidence, plan work, run supervised tools, review results, and preserve project context. That workflow earns daily retention before Astravox expands into every field.

## Operating principles

1. **Trust before autonomy.** Agents show plans and actions; meaningful side effects require approval.
2. **One workspace.** Chat, projects, memory, knowledge, and tasks share identity, permissions, and history.
3. **Evidence over assertion.** Grounded answers cite sources; agents show logs, diffs, and test evidence.
4. **Privacy by default.** Data ownership, retention, export, deletion, and connector permissions are explicit.
5. **Measure quality.** Evaluate task success, grounding, safety, latency, reliability, retention, and unit cost.
6. **Build reusable primitives.** Models, tools, connectors, memory, jobs, and policies remain modular.
7. **Expand safely.** High-risk domains require extra controls and domain expertise.

## Definition of done

Every shipped capability requires:

- a documented user journey and API contract;
- authentication, authorization, validation, and secure defaults;
- accessible loading, empty, success, and failure states;
- unit tests plus integration or end-to-end coverage where appropriate;
- logs, metrics, traces, and operational alerts;
- privacy, retention, audit, and cost behavior;
- a migration and rollback plan; and
- updated README, API, architecture, and changelog documentation when relevant.

## Roadmap at a glance

| Phase | Product outcome | Core investment |
| --- | --- | --- |
| 0 | Reliable foundation | Architecture, testing, CI, security, observability |
| 1 | Premium AI chat | Streaming, rich messages, conversations, accessibility |
| 2 | Persistent workspace | Projects, files, tasks, sharing, activity history |
| 3 | Trusted knowledge | Ingestion, cited RAG, inspectable memory, permissions |
| 4 | Model intelligence | Multi-model gateway, routing, evaluations, cost control |
| 5 | Supervised agents | Jobs, tools, sandboxes, approvals, audit trails |
| 6 | Developer and automation platform | Code workspace, connectors, workflows, public API |
| 7 | Multimodal intelligence | Vision, OCR, voice, real-time interactions |
| 8 | Team and enterprise | Organizations, RBAC, SSO, billing, compliance |
| 9 | Reliability at scale | SLOs, disaster recovery, capacity, security operations |
| 10 | Vertical solutions | Domain workflows on the shared platform |

## Phase 0 - Platform foundation and engineering discipline

**Goal:** make the product safe and inexpensive to evolve.

### Deliverables

- Clear presentation, application, domain, infrastructure, and database boundaries.
- Typed frontend components and stable backend schemas.
- Environment validation, secret management, configuration profiles, and migration discipline.
- Central error handling, structured logs, request IDs, traces, and security event logging.
- Automated builds, tests, linting, dependency checks, and deploy previews.
- Rate limiting, secure headers, JWT validation, row-level tenant isolation, and audit foundations.
- Product analytics taxonomy for activation, retention, task success, latency, and AI cost.

### Exit criteria

- Clean build and repeatable local environment.
- Critical authorization policies have automated coverage.
- No secrets in tracked files; dependency and secret scans run in CI.
- Incidents can be correlated across browser, API, background job, model, and connector events.

### Delivered in the current increment

- Every HTTP response receives a safe `X-Request-ID`; valid IDs from the frontend
  or an edge gateway are propagated for end-to-end correlation.
- Security regression tests cover generated, propagated, and rejected request IDs.
- GitHub Actions now runs backend tests and the production frontend build on every
  pull request and on pushes to the default branches.

## Phase 1 - Premium AI chat

**Goal:** create the daily-use surface that feels excellent before adding complexity.

### Deliverables

- Responsive desktop and mobile layout with conversation rail, composer, context rail, and project switcher.
- Reliable token streaming, stop, retry, regenerate, continuation, and provider fallback.
- Sanitized Markdown, tables, Mermaid, syntax-highlighted code, copy actions, link previews, and artifact rendering.
- Message editing, branching, response comparison, pinning, archiving, searchable history, and export.
- File upload with type/size validation, safe preview, malware scanning integration point, and processing status.
- Keyboard shortcuts, command palette, screen-reader support, reduced-motion behavior, and internationalization readiness.
- Explicit model selection plus a transparent best-model route with request-level model and cost visibility.

### Exit criteria

- Core chat works accessibly on desktop and mobile.
- Streaming is cancellable and errors never lose the user's prompt.
- Rendering and uploads are safe against XSS and unsafe file content.
- Conversation actions are persisted and covered by user-flow tests.

## Phase 2 - Projects, workspaces, and collaboration

**Goal:** turn individual conversations into durable work.

### Deliverables

- Personal workspaces, organizations, projects, membership, roles, invitations, and scoped permissions.
- Project conversations, files, notes, tasks, milestones, decisions, and generated artifacts.
- Kanban/list task views, assignees, due dates, dependencies, recurring tasks, and AI project updates.
- Shared links, comments, mentions, notifications, presence, activity feed, version history, and restore points.
- Project templates for software delivery, research, education, business planning, content, and operations.
- Workspace-wide search with source-aware filtering.

### Exit criteria

- A team can create, share, resume, export, and archive a project without losing context.
- Tenant and project isolation is proven through tests.
- Every shared-resource change is attributable in activity and audit history.

## Phase 3 - Knowledge, retrieval, and memory

**Goal:** provide answers grounded in user-controlled, permission-aware information.

### Deliverables

- Ingestion for PDF, DOCX, PPTX, Markdown, TXT, CSV, XLSX, images, web pages, GitHub repositories, local files, and approved cloud sources.
- Parsing, OCR, malware-scanning hook, normalization, chunking, embedding, metadata extraction, deduplication, versioning, and job progress.
- Hybrid retrieval: keyword, semantic, metadata filtering, reranking, recency, and source-permission enforcement.
- Source citations that open the exact file location, page, paragraph, or web fragment used in an answer.
- Knowledge collections, access policies, freshness status, source sync schedules, and failed-sync recovery.
- Short-term, semantic, episodic, workspace, and procedural memory with inspect, edit, pin, export, and delete controls.
- Retrieval evaluations using curated question sets, citation-correctness checks, and permission-leak tests.

### Exit criteria

- Every grounded answer can show its evidence.
- Users can delete or correct memory and observe the change end to end.
- Unauthorized documents never enter results, citations, or model context.
- Retrieval quality, latency, and cost are measured continuously.

## Phase 4 - Multi-model intelligence platform

**Goal:** make Astravox AI provider-flexible, resilient, and cost-aware.

### Deliverables

- Provider adapters for OpenAI, Anthropic, Gemini, and approved open-source or self-hosted models.
- Capability registry for context window, modality, tools, structured output, reasoning, region, privacy, and pricing.
- Routing by quality, latency, availability, privacy, workload, user preference, and budget.
- Fallbacks, provider health checks, circuit breakers, retries, idempotency, and graceful degraded modes.
- Prompt templates, versioning, experiments, feature flags, structured outputs, and schema validation.
- Per-user, project, workspace, and organization metering, spend limits, alerts, and chargeback reporting.
- Offline and online evaluations for response quality, safety, tool selection, and retrieval grounding.

### Exit criteria

- Providers can change without breaking UI or API contracts.
- The system records why a route was chosen and what it cost.
- Release candidates pass agreed evaluation thresholds before rollout.

## Phase 5 - Supervised multi-agent execution

**Goal:** automate real workflows without opaque or uncontrolled behavior.

### Deliverables

- Orchestrator roles: planner, researcher, coder, browser, file, memory, reviewer, tester, and deployment.
- Durable task graphs with queues, checkpoints, retries, deadlines, cancellation, resumability, and human handoff.
- Visible execution view: plan, live status, tool calls, terminal output, citations, files changed, tests run, and final summary.
- Tool manifests with JSON schemas, scopes, policy checks, budgets, rate limits, and redaction rules.
- Approval gates for external communication, credential use, payment, destructive changes, data egress, deployment, and production access.
- Isolated code sandboxes with ephemeral credentials, resource quotas, network egress policy, package allowlists, and artifact retention.
- Agent evaluations for planning quality, completion, unsafe-action rate, recovery, and cost per successful task.

### Exit criteria

- Every agent run has an audit trail from request to result.
- Risky actions pause for human approval.
- Agent tools cannot access the host, arbitrary credentials, or unrestricted network resources.
- Failed tasks are diagnosable, safely resumable, and never silently change user data.

## Phase 6 - Developer platform and automation

**Goal:** become the place where technical teams plan, build, verify, and ship software safely.

### Deliverables

- File explorer, code editor, diff viewer, terminal panel, test results, logs, and deployment status.
- GitHub integration for repositories, issues, pull requests, branches, code review, and CI status using least-privilege OAuth scopes.
- Browser automation with isolated sessions, explicit domain policy, screenshots, recordings, and approval for authenticated or external actions.
- Connector framework for Drive, Slack, Notion, Jira, Linear, databases, and internal APIs with per-connector permissions and sync health.
- Workflow builder for triggers, approvals, schedules, webhooks, and reusable agent playbooks.
- Public developer API, API keys, service accounts, SDKs, webhooks, rate limits, documentation, and sandbox environment.
- Template marketplace for user-owned project templates, prompts, workflows, and approved tools.

### Exit criteria

- A development project can progress from issue to branch, implementation, test evidence, review, and approved deployment.
- Connectors can be revoked, audited, and isolated by workspace.
- API consumers have stable contracts, quotas, and observability.

## Phase 7 - Multimodal and real-time AI

**Goal:** let users work naturally with visual and spoken information.

### Deliverables

- Image, screenshot, diagram, chart, and document understanding with visual citations when supported.
- OCR correction UI, table extraction review, and confidence/error feedback.
- Speech-to-text, text-to-speech, voice commands, live transcript, interruption handling, and language selection.
- Camera and screen-share workflows with explicit consent, visible recording state, and data-handling disclosures.
- Multimodal artifact generation and structured extraction into tasks, notes, tables, and knowledge collections.

### Exit criteria

- Media processing has explicit consent, retention, and deletion behavior.
- Users can correct extracted data before automation relies on it.
- Voice and visual surfaces meet accessibility and privacy requirements.

## Phase 8 - Enterprise, monetization, and governance

**Goal:** make Astravox AI deployable in organizations with serious data and operational requirements.

### Deliverables

- Organizations, granular RBAC/ABAC, group mapping, service accounts, and delegated administration.
- SSO through SAML/OIDC, SCIM provisioning, domain verification, session controls, and enterprise onboarding.
- Immutable audit logs, data residency options, retention, legal hold, export, deletion, and backup controls.
- Encryption in transit and at rest, managed secrets, key rotation, tenant isolation tests, threat modeling, and incident runbooks.
- Free, Pro, Team, and Enterprise plans; usage-based agent/compute charges, invoices, entitlements, trials, and upgrades.
- Admin console for users, policies, models, connectors, data sources, budgets, usage analytics, and support diagnostics.
- SOC 2 readiness, vendor review, privacy documentation, penetration testing, and disaster-recovery exercises.

### Exit criteria

- Administrators can control identity, data, spend, models, connectors, and audit exports.
- Security and operational controls have evidence appropriate for target customers.
- Billing and quota enforcement are accurate, explainable, and tested.

## Phase 9 - Reliability, security operations, and scale

**Goal:** reliably serve growing customer workloads.

### Deliverables

- Service-level objectives for availability, latency, streaming, ingestion, retrieval, agent completion, and support.
- Metrics, logs, traces, alert routing, synthetic checks, incident management, postmortems, and public status communication.
- Load tests, resilience drills, queue back-pressure, autoscaling, database performance baselines, and capacity forecasts.
- Backup/restore drills, multi-region recovery strategy, disaster-recovery objectives, and rollback rehearsals.
- Vulnerability management, dependency updates, DAST/SAST, secret scanning, penetration tests, and LLM-threat red-team exercises.
- FinOps reporting for models, embeddings, storage, sandboxes, connectors, and infrastructure cost per successful customer outcome.

### Exit criteria

- SLO performance is monitored and owned.
- Recovery objectives are tested rather than assumed.
- Security findings, incidents, and cost anomalies have documented response procedures.

## Phase 10 - Expert modes and vertical solutions

**Goal:** deliver specialized value without fragmenting the platform.

### Foundation modes

- **Programming AI:** codebase-aware planning, implementation, test generation, review, and deployment assistance.
- **Research AI:** literature review, source comparison, citations, evidence tables, and research briefs.
- **Education AI:** tutoring, study plans, formative assessment, document feedback, and learning projects.
- **Business AI:** analysis, reports, operational playbooks, customer research, and decision support.
- **Creative AI:** writing rooms, content workflows, brand systems, and asset ideation.
- **Language AI:** translation, language learning, transcription, and localized document workflows.

### High-risk modes, gated by controls and expertise

- **Medical AI:** education and workflow support only until clinically validated; provenance and expert governance required.
- **Legal AI:** document assistance with jurisdiction awareness, provenance, disclaimers, and legal-review workflow.
- **Finance and trading AI:** research and analysis with data licensing, suitability controls, and no unapproved execution authority.
- **Cybersecurity AI:** defensive analysis, secure sandboxes, abuse detection, and restrictions around harmful actions.

No vertical mode can bypass core permissions, audit trails, evaluations, or safety policies.

## Milestones and success metrics

### First 90 days

1. Finish the premium chat shell and robust streaming.
2. Ship project/workspace data models and permission boundaries.
3. Ship secure uploads and cited retrieval for a focused source set.
4. Ship a supervised agent run with plan, tools, approval, and audit trail.
5. Establish model routing, evaluation baselines, and cost dashboards.
6. Recruit 10-20 design partners in the developer/research wedge.

### 6-12 month target

- Daily-returning teams use Astravox AI for a complete recurring workflow.
- Retrieval answers are measurably grounded and permission-safe.
- Agents complete bounded, valuable tasks with human approvals and test evidence.
- Teams manage access, spend, data, and connectors from one admin surface.
- Product decisions are guided by activation, retention, success rate, quality, reliability, and gross-margin metrics.

### Core metrics

| Area | Metrics |
| --- | --- |
| Customer value | Activation, weekly retained teams, successful tasks, time saved, user satisfaction |
| AI quality | Grounded-answer score, citation correctness, task completion, unsafe-action rate |
| Reliability | Availability, p95 latency, streaming completion, queue delay, incident recovery time |
| Security | Authorization coverage, vulnerability remediation time, policy violations, audit completeness |
| Economics | Cost per successful task, gross margin, routing savings, expansion revenue |

## What we deliberately do not do first

Native mobile apps, a full plugin marketplace, every enterprise connector, always-on voice, autonomous production deployment, and every expert mode are later investments. Each matters only after Astravox AI has a proven daily-use workflow and the guardrails to operate it safely.

## Architectural direction

| Area | Direction |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, accessible responsive design system |
| Backend | FastAPI organized into application, domain, infrastructure, and API layers |
| Data | PostgreSQL/Supabase for transactions, pgvector for embeddings, object storage for files |
| Jobs and cache | Redis-backed caching and durable background job orchestration where justified |
| AI | Provider adapters behind stable contracts for chat, embeddings, tools, speech, and vision |
| Security | JWT/RLS enforcement, least privilege, audit logs, encryption, secrets, policy engine |
| Operations | GitHub Actions CI/CD, observability, feature flags, evaluation gates, safe rollouts |

## Final standard

Astravox AI becomes best in class by being **useful enough to return to every day, safe enough to trust with real work, and extensible enough to serve many fields without becoming a collection of disconnected features**. Every roadmap item must make the system clearer, more reliable, and more valuable for its users.
