# Deployment Guide

This guide covers deploying the canonical AstroVoxAI stack: **Vite/React frontend → FastAPI backend → Supabase Postgres**.

## 1. Environment variables

Set these in your hosting platform (never commit real values). See `.env.example`.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `VITE_SUPABASE_URL` | frontend (build time) | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | frontend (build time) | Supabase anon key |
| `VITE_API_URL` | frontend (build time) | Backend base URL. If unset, frontend uses `/api` and requires a reverse proxy. |
| `OPENAI_API_KEY` | backend | OpenAI API access |
| `ALLOWED_ORIGINS` | backend | Comma-separated allowed CORS origins (your deployed frontend URL) |
| `LOG_LEVEL` | backend | `DEBUG`/`INFO`/`WARNING`/`ERROR` (default `INFO`) |
| `RATE_LIMIT` | backend | Per-IP limit, slowapi syntax (default `120/minute`) |

> **Note:** `VITE_*` variables are baked into the frontend bundle at build time and are publicly visible. Only the Supabase anon key (protected by RLS) belongs there — never put service-role or OpenAI keys in `VITE_*`.

## 2. Database

In the Supabase SQL editor, run in order:

1. `database/schemas/supabase_setup.sql` — tables, Row-Level Security, and per-user policies.
2. `database/migrations/0001_indexes_and_signup_trigger.sql` — indexes on hot paths and the `on_auth_user_created` trigger that provisions a profile + settings row on signup. The migration is idempotent (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`, `DROP TRIGGER IF EXISTS`) and safe to re-run.

## 3. Backend (FastAPI)

### Docker
```bash
cd 02-Backend
docker build -t astravox-backend .
docker run -p 8000:8000 --env-file ../.env astravox-backend
```
The image runs as a non-root user and exposes a `/health/liveness` HEALTHCHECK.

### Without Docker
```bash
cd 02-Backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For multiple workers behind a process manager, use:
`uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`.

Health/probe endpoints: `/health`, `/health/readiness`, `/health/liveness`. Interactive API docs at `/docs`.

## 4. Frontend (Vite/React)

```bash
npm ci
npm run build      # outputs static assets to dist/
```

Serve `dist/` from any static host (Vercel, Netlify, Cloudflare Pages, S3+CDN, nginx). Configure either:
- `VITE_API_URL` pointing directly at the backend (ensure `ALLOWED_ORIGINS` includes the frontend origin), **or**
- a reverse proxy that forwards `/api` to the backend (then `VITE_API_URL` can be left unset).

## 5. CI

`.github/workflows/ci.yml` runs frontend build, backend lint + tests, and a gitleaks secret scan on every push/PR to `main`.

## 6. Security checklist

- [ ] Rotate any credential that ever appeared in git history (a Gemini key was previously committed — it must be rotated even though the file was removed).
- [ ] `ALLOWED_ORIGINS` set to the exact deployed frontend origin(s), not `*`.
- [ ] Supabase RLS enabled (it is in `supabase_setup.sql`) and policies reviewed.
- [ ] Secrets provided via the platform's secret store, not committed.
- [ ] HTTPS terminated at the load balancer / CDN.
