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
python -m pytest tests/security -q        # 142 passed, 0 failed
python -m pytest evals -q                 # 40 passed (golden set + grader)
python -m pytest tests/integration/test_auth_flow.py -q  # 14 passed
```

The security chunk is the one that carries the controls: token delivery by
email only, refresh tokens never in a query string, provider-verified OAuth,
brute-force lockout, tenant isolation, the cost gate, and the RLS
migration's coverage. It was 59 passed / 20 failed before the fixes in
`SECURITY_BACKLOG.md`; the failures were real, not cosmetic.

`tests/integration` and the rest of the suite do not complete as a single
run — modules in it make real network calls or block on a condition that
never fires. The baseline is per-chunk and says so.

Working and covered by tests:

- Auth flow: signup, login, logout, password reset, `/auth/me`
- Multi-provider adapter layer (see the table below)
- API gateway: rate limiting, CSRF, IP allowlist, HTTPS enforcement,
  idempotency, request limits, error envelope
- Tenant isolation: RBAC, data path, and RLS policies
- AI spend cap: cost-aware, enforced before the provider call
- Observability: structured JSON logs, Prometheus metrics

Provider adapters exist behind one interface. Runtime connectivity is **not**
verified — no provider API key is configured in this environment, so the
adapters are exercised through fakes.

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

## Maintainer and provenance

One maintainer. The commit history is majority machine-authored: `Lovable`,
`Devin AI` and `gpt-engineer-app[bot]` account for most of it, which is why a
code audit found the failure modes it did — a stack whose Dockerfiles had
never been started, an auth path returning verification tokens to
unauthenticated callers, and a CI gate that compared the threshold to itself
and always passed. None of that is unusual for generated scaffolding; it is
only a problem if the repository does not say so.

What has since been verified is in `SECURITY.md` and `SECURITY_BACKLOG.md`,
with the measurement method in `docs/BASELINE.md`. What is still open is
listed there rather than implied away.

The Go engine is not benchmarked against llama.cpp or vLLM, so no claim is
made that it beats them. Its package count is not a differentiator and is
not presented as one.

## Security

`SECURITY.md` covers reporting, severity priorities, and the known gaps.
`SECURITY_BACKLOG.md` is the live state: what is fixed and tested, what is
done but unverified here, and what is still open.
`docs/SECRET_ROTATION.md` is the rotation order for anything that has been
in a real environment.
`docs/E2E_STATUS.md` records which end-to-end tests are written but have
never run.

## Layout

```
02-Backend/          FastAPI application (app/, tests/, migrations/)
frontend/  web/  src  frontend sources
cmd/astrovox         Go CLI
internal/  tensor/   Go engine
evals/               golden task set, grader, and regression gate
supabase/migrations/ RLS tenant-isolation policies
docs/
  BASELINE.md        measured test results, and what was broken before
  SECURITY.md        reporting, severity priorities, known gaps
  SECURITY_BACKLOG.md  live security state: fixed / unverified / open
  SECRET_ROTATION.md   rotation order for live secrets
  E2E_STATUS.md      which E2E tests are written but never executed
  MODULE_INVENTORY.md  which modules the product actually uses (D01-10)
  IMPOSSIBLE_MODE_DELIVERY.md  engine design notes
  adr/               architecture decision records (D29-02)
  research/          OS, database, kernel and compiler theory notes
tools/               check_live_imports.py — enforces D01-11
nginx.conf           nginx vhost (HTTP only; TLS is terminated upstream)
```

## Getting started

Backend:

```bash
cd 02-Backend
python -m pip install -e .
python -m pytest tests/security -q           # 142 passed, 0 failed
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
