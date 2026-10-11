# AstrovoxAI

A FastAPI chat backend with multi-provider LLM routing, plus a separately
developed Go inference engine.

**Read this first.** The repository contains two distinct projects:

| Path | What it is | State |
|---|---|---|
| `02-Backend/`, `frontend/`, `web/` | Python FastAPI chat platform (the product) | see `docs/BASELINE.md` |
| `internal/`, `tensor/`, `cmd/`, `compiler/` | Go tensor/inference engine | `go test ./...` clean, 1,364 test functions |

The two are not connected. The Go engine does not serve the FastAPI app, and the
app does not call the Go engine.

## What this repository is not

No frontier model is trained here. There is no proprietary model — requests are
routed to third-party providers. The claims previously in this README
("RLHF", "Robotics", "Quantum-ready", "SOC 2 controls", "distributed training")
described scaffolding and research modules, not shipped capability. An import
graph of the live product found **7 of 114** top-level modules actually used; see
`docs/MODULE_INVENTORY.md` and ADR-0006.

Claims are limited to what a test or a run demonstrates.

## Product: FastAPI chat backend

Verified state (`docs/BASELINE.md`):

```
python -m pytest tests --collect-only -q     # 6495 collected, 0 errors
python -m pytest tests/integration -q        # auth flow: 11 passed, 1 failed*
```

\* the remaining failure needs a reachable Supabase; importing `app.main`
attempts a connection and retries (~27s). Environment-bound, not a code defect.

Working and covered by tests:

- Auth flow: signup, login, logout, password reset, `/auth/me`
- Multi-provider adapter layer (see the table below)
- API gateway: rate limiting, CSRF, IP allowlist, HTTPS enforcement,
  idempotency, request limits, error envelope
- Observability: structured JSON logs, Prometheus metrics

Provider adapters exist behind one interface. Runtime connectivity is **not**
verified — no provider API key is configured in this environment, so the
adapters are exercised through recorded fakes.

| Provider | Adapter path | Runtime verified |
|---|---|---|
| OpenAI | `app/adapters/openai_adapter.py` | no |
| Anthropic | `app/adapters/*` | no |
| Gemini | `app/adapters/gemini_adapter.py` | no |
| Local | `app/adapters/local*` | no |

## Engine: Go tensor/inference engine

A self-contained tensor and inference engine with its own test suite.

- Tensor core, blocked GEMM, FFT, Winograd, Flash Attention, quantization
- Autograd, compiler IR with dataflow and polyhedral optimisation
- Distributed runtime: tensor/pipeline/data parallelism, RPC, elastic training
- Backends with CPU fallback: CUDA, Vulkan, Metal, DirectML, ROCm, OpenCL, WebGPU

```bash
go build ./... && go vet ./... && go test -p 2 ./...
```

Design records: `docs/IMPOSSIBLE_MODE_DELIVERY.md`.

## Layout

```
02-Backend/          FastAPI application (app/, tests/, migrations/)
frontend/  web/  src  frontend sources
cmd/astrovox         Go CLI
internal/  tensor/   Go engine
docs/
  BASELINE.md        measured test results, and what was broken before
  MODULE_INVENTORY.md  which modules the product actually uses (D01-10)
  IMPOSSIBLE_MODE_DELIVERY.md  engine design notes
  adr/               architecture decision records (D29-02)
  research/          OS, database, kernel and compiler theory notes
tools/               check_live_imports.py — enforces D01-11
```

## Getting started

Backend:

```bash
cd 02-Backend
python -m pip install -e .
python -m pytest tests --collect-only -q      # 6495 tests, 0 errors
```

Engine:

```bash
go test -p 2 ./...
```

Or open the repository in a dev container (`.devcontainer/`), which installs both
toolchains. VS Code tasks for verify, lint, and the import-boundary check are in
`.vscode/tasks.json`.

## One-command verification

`make verify` runs lint, typecheck, tests and build. The same command is mirrored
in CI (`.github/workflows/ci.yml`).

## Contributing

`docs/CONTRIBUTING.md` and `.github/PULL_REQUEST_TEMPLATE.md`. Branch protection
requires review before merge to `main`.
