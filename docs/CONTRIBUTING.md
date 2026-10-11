# Contributing to AstrovoxAI

## Read this first

This repository contains two projects that are **not** connected:

- `02-Backend/`, `frontend/` — the Python FastAPI chat platform.
- `internal/`, `tensor/`, `cmd/` — a Go inference engine.

Work in one at a time. Do not assume a change in one is visible from the other.

## Before you start

1. Check `docs/MODULE_INVENTORY.md`. If the module you are about to edit is not
   in the live set, your change may be quarantined code — say so in the PR.
2. Read the relevant ADR in `docs/adr/`. If your change contradicts one, the ADR
   needs updating in the same PR, not silently.

## Local setup

Open the repo in a dev container (`.devcontainer/`) for a reproducible
toolchain. Otherwise:

```bash
cd 02-Backend && python -m pip install -e .    # backend
go build ./...                                  # engine
```

## Verify before pushing

```bash
make verify          # lint, typecheck, tests, build
python tools/check_live_imports.py   # D01-11 boundary
```

Pre-commit hooks (`pre-commit install`) run the same checks locally.

## Adding tests

- Tests go in `02-Backend/tests/`, named `test_*.py`.
- **A test that needs an external service must say so** and be runnable without
  one: use the recorded fakes in `tests/integration/conftest.py` rather than a
  live provider.
- Do not add tests that pad a coverage number. A test that asserts nothing
  meaningful gets removed.
- Experimental modules are excluded from collection (`norecursedirs` in
  `pytest.ini`). Moving a test out of that directory re-enables it — make sure
  its import surface works first.

## Rules that block a merge

1. `go build ./...`, `go vet ./...`, `go test -p 2 ./...` clean.
2. Backend suite collects with 0 errors (`pytest tests --collect-only -q`).
3. `tools/check_live_imports.py` passes.
4. `gofmt -l .` is empty for files you touched.
5. No secrets, no new `VITE_`-prefixed variable (see D01-03), no large binaries.
6. Every claim in the PR description maps to something the tests demonstrate.

## Commits

Write what changed and why, not a changelog. If a commit fixes a bug found by
running the suite, say what the symptom was.

## Review

One approval required for `main`. Reviewers check the two things CI cannot:
does the change belong in this module, and does the test actually assert the
behaviour it claims.

## Reporting security issues

See `SECURITY.md`. Do not open a public issue for anything that looks like a
credential exposure.