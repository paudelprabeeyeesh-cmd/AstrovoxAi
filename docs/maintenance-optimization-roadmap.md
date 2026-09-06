# AstrovoxAI Backend — Maintenance & Optimization Roadmap

This roadmap provides a structured, phased approach for sustaining and improving the
`02-Backend` service. Each phase is actionable and concludes with a **version-control
commit boundary**: every task described here must be committed immediately after
completion so that work remains reviewable, revertible, and synchronized with Lovable's
connected branch.

## Phase 1 — Stabilize

Goal: eliminate regressions, reduce crash surfaces, and preserve green tests.

### Task 1.1 — Bug triage & incident capture
- Instrument `app.exceptions.AstrovoxError` subclasses with structured context fields
  (`provider`, `model_id`, `tenant_id`, `request_id`).
- Add an `unhandled_exception` handler in the ASGI middleware stack that captures the
  traceback and enqueues it for review.
- **Commit boundary**: each new exception subclass + its ASGI wiring is one commit.

### Task 1.2 — Test-suite enforcement
- Configure `pytest.ini` / `pyproject.toml` with `--strict-markers`, `--tb=short`, and
  a CI threshold (fail build if coverage drops below current baseline).
- Add a `tests/conftest.py` fixture that automatically mocks external provider HTTP
  calls to keep tests deterministic.
- **Commit boundary**: one commit per configuration change plus the shared fixture.

### Task 1.3 — Static analysis hygiene
- Run `ruff check .` and `mypy app/` in CI; fix all reported issues before new
  feature work proceeds.
- Treat every lint or typing error as a standalone commit to keep diffs reviewable.
- **Commit boundary**: each lint fix batch is a commit.

### Task 1.4 — Completed refactor: centralize shared utilities
- ✅ `CircuitState` enum deduplicated into `app/utils.py`.
- ✅ `now()` helper replaces direct `time.time()` calls in core modules
  (`executor`, `jobs`, `agent`, `knowledge_base`, `ai_kernel`, `multi_agent`,
  `workflow_engine`).
- **Commit boundary**: one commit per module refactored (already completed).

## Phase 2 — Simplify

Goal: reduce cognitive load, collapse redundant modules, and make navigation trivial.

### Task 2.1 — Audit file count & module responsibilities
- Run a tree-based audit to identify files > 600 LOC or with > 3 distinct
  responsibilities (e.g., `caching.py`, `circuit_breaker.py`).
- Produce a `docs/refactor-candidates.md` mapping each oversized file to a proposed
  split.
- **Commit boundary**: document commit first; each split is a subsequent commit.

### Task 2.2 — Directory restructuring
- Consolidate `app/providers/` subpackages that expose only 1–2 classes into a
  single `providers/core.py` module.
- Move rarely used utilities (`app/utils.py` extensions, analytics helpers) into a
  `libs/` package.
- **Commit boundary**: move + rename each package as an atomic commit.

### Task 2.3 — Eliminate enum duplication
- ✅ `CircuitState` moved to `app/utils.py`.
- Compare `AgentState` in `app/agent.py` vs `app/multi_agent.py`. If they diverge
  intentionally, document the difference in `docs/enums.md`; if they overlap,
  merge into `app/utils.py`.
- **Commit boundary**: one commit per enum deduplication.

### Task 2.4 — Remove dead imports & unused dependencies
- Use `ruff` to flag unused imports; delete them module-by-module.
- Audit `requirements.txt` for packages with no import references in `app/`.
- **Commit boundary**: one commit per module or dependency batch.

## Phase 3 — Optimize

Goal: lower latency, reduce memory, and measure every change.

### Task 3.1 — Baseline profiling
- Run `python -m cProfile -o profile.out` on representative endpoints (chat,
  upload, workflow trigger).
- Use `snakeviz profile.out` or `py-spy record` to identify top-10 hot functions.
- Document the baseline in `docs/performance-baseline.md`.
- **Commit boundary**: profiling scripts + baseline report commit.

### Task 3.2 — Startup time reduction
- Lazy-load heavy singletons (`knowledge_base`, `executor`, `workflow_engine`)
  behind function calls instead of module-import side effects.
- Measure cold-start time before/after with `time.perf_counter()`.
- **Commit boundary**: one commit per lazy-load refactor.

### Task 3.3 — Memory footprint optimization
- Replace in-memory dictionaries holding large payloads (e.g., `caching.py`,
  `analytics.py`) with bounded LRU caches (`functools.lru_cache` or
  `cachetools.LRUCache`).
- Add `__slots__` to hot dataclasses (`Job`, `Task`, `WorkflowExecution`) after
  confirming memory savings with `tracemalloc`.
- **Commit boundary**: one commit per memory optimization.

### Task 3.4 — Async I/O audit
- Scan for synchronous `requests` / `time.sleep` calls in `async` functions.
- Replace with `httpx.AsyncClient` + `asyncio.sleep`.
- **Commit boundary**: one commit per module converted.

## Phase 4 — Harden

Goal: achieve production-grade reliability and security posture.

### Task 4.1 — Security audit
- Run `bandit -r app/` and `pip-audit` against `requirements.txt`.
- Document every finding in `docs/security-findings.md` with severity, owner, and fix
  plan.
- **Commit boundary**: one commit per severity tier (critical → high → medium → low).

### Task 4.2 — Robust error handling
- Wrap all external HTTP calls with `tenacity` retry policies (exponential backoff,
  jitter, circuit-breaker fallback).
- Ensure every `try` block has an `except` that logs context and re-raises or
  degrades gracefully.
- **Commit boundary**: one commit per module hardened.

### Task 4.3 — Crash recovery & checkpoint testing
- For `ai_kernel.py` and `workflow_engine.py`, write integration tests that:
  1. Start an execution
  2. Kill the process
  3. Restore from checkpoint / re-hydrate state
  4. Assert continuation or correct failure state
- **Commit boundary**: one commit per checkpoint test suite.

### Task 4.4 — Secret & credential hygiene
- Audit `app/api_security.py`, `app/advanced_security.py`, and environment
  variable usage for hardcoded credentials.
- Ensure all secrets come from environment variables or a secret manager.
- Document rotation policy in `docs/security/CREDENTIAL_PURGE.md`.
- **Commit boundary**: one commit per secret remediation.

## Phase 5 — Polish

Goal: improve developer and end-user experience through clarity and consistency.

### Task 5.1 — Logging standardization
- Define a structured log schema: `{"ts", "level", "logger", "msg", "context",
  "trace_id"}`.
- Migrate `logging` calls to use `structlog` or a consistent `LoggerAdapter`.
- **Commit boundary**: one commit per logger migration batch.

### Task 5.2 — CLI & developer tooling
- Add a `Makefile` or `justfile` with commands: `lint`, `typecheck`, `test`,
  `profile`, `migrate`, `seed`.
- Ensure every command is idempotent and documented in `docs/developer-tools.md`.
- **Commit boundary**: one commit per tool added.

### Task 5.3 — Documentation generation
- Ensure every public function and class has a Google-style docstring.
- Run `pdoc --html app/ -o docs/api/` and review the output for completeness.
- **Commit boundary**: one commit per documentation section (API, guides, examples).

### Task 5.4 — Error-message clarity
- Audit `AstrovoxError` subclasses for user-facing messages; replace technical jargon
  with actionable guidance.
- Add error codes and a public error-reference page in `docs/errors.md`.
- **Commit boundary**: one commit per error-message batch.

## Phase 6 — Validate

Goal: confirm the system behaves correctly under real-world conditions.

### Task 6.1 — Real-world endpoint testing
- Deploy to a staging environment and run load tests (`locust` or `k6`) against
  chat, agent reasoning, and workflow endpoints.
- Set SLOs: p95 latency < 500 ms, error rate < 0.5%.
- **Commit boundary**: one commit per test script + results artifact.

### Task 6.2 — Feedback integration loop
- Instrument `app/analytics.py` to capture user-impacting errors with anonymized
  metadata.
- Create a `docs/feedback-log.md` template; review weekly.
- **Commit boundary**: one commit per instrumentation change.

### Task 6.3 — Developer API refinement
- Review `app/providers/` interfaces for consistency (method signatures, return
  types, error contracts).
- Publish an OpenAPI spec or typed interface contract for internal consumers.
- **Commit boundary**: one commit per interface revision.

## Phase 7 — Maintain

Goal: sustain health without accumulating new debt.

### Task 7.1 — Dependency management
- Enable `dependabot` or `renovate` for automated PRs.
- Review dependency updates weekly; merge only after tests pass.
- **Commit boundary**: merge commit per dependency PR; do not squash-and-merge
  without review.

### Task 7.2 — Iterative refactoring cadence
- Reserve 20% of each sprint for Phase 1–3 tasks.
- Track technical-debt tickets in the project board with clear acceptance criteria.
- **Commit boundary**: one commit per refactoring task, linked to the ticket.

### Task 7.3 — Quality gates
- Add a GitHub Actions workflow (or equivalent) that blocks merges when:
  - Tests fail
  - Lint errors appear
  - Coverage drops
  - Security scan finds new high/critical findings
- **Commit boundary**: workflow definition commit + any required configuration updates.

## Commit Discipline

Every task in this roadmap is designed to be **atomic and independently reviewable**.
No task should span multiple commits unless explicitly noted. After each commit:

1. Run `git status` to verify the working tree is clean.
2. Run `git push` (or equivalent) to sync the commit to the connected branch.
3. Verify CI passes before beginning the next task.

This ensures that Lovable's editor and any reviewers always have a working, buildable
revision to inspect.

---

*Last updated: 2026-09-06*
