# AstrovoxAI Backend — Maintenance & Optimization Roadmap

## Phase 1: Stabilize

Focus: bug resolution, technical debt reduction, and maintaining test suite integrity.

### Task 1.1 — Bug Triage & Incident Capture
- Instrument `app.exceptions.AstrovoxError` subclasses with structured context fields (`provider`, `model_id`, `tenant_id`, `request_id`).
- Add an `unhandled_exception` handler in the ASGI middleware stack that captures the traceback and enqueues it for review.
- **Commit boundary**: each new exception subclass + its ASGI wiring is one commit.

### Task 1.2 — Test-Suite Enforcement
- Configure `pytest.ini` / `pyproject.toml` with `--strict-markers`, `--tb=short`, and a CI threshold (fail build if coverage drops below current baseline).
- Add a `tests/conftest.py` fixture that automatically mocks external provider HTTP calls to keep tests deterministic.
- **Commit boundary**: one commit per configuration change plus the shared fixture.

### Task 1.3 — Static Analysis Hygiene
- Run `ruff check .` and `mypy app/` in CI; fix all reported issues before new feature work proceeds.
- Treat every lint or typing error as a standalone commit to keep diffs reviewable.
- **Commit boundary**: each lint fix batch is a commit.

### Task 1.4 — Completed Refactor: Centralize Shared Utilities
- `CircuitState` enum deduplicated into `app/utils.py`.
- `now()` helper replaces direct `time.time()` calls in core modules (`executor`, `jobs`, `agent`, `knowledge_base`, `ai_kernel`, `multi_agent`, `workflow_engine`).
- **Commit boundary**: one commit per module refactored.
