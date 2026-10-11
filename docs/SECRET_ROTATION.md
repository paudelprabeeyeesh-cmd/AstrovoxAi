# Secret Rotation Checklist

Generated from the full-history secret scan (`python tools/secret_scan.py`,
values redacted) and the `.env` untracking. The scan itself found **no
high-confidence secrets in reachable history**. This checklist is therefore
precautionary: it covers the secrets that are at risk from (a) the junk
`.env` that was tracked until now, and (b) any secret ever set in a deploy
environment that reused that `.env`.

## What the scan covered

Patterns checked across 38 refs, matched values redacted from output:
Supabase `service_role`, any JWT-shaped string, OpenAI, Anthropic, AWS
access key id, PEM private key blocks, Slack, GitHub PATs, Stripe secret
and webhook secrets, privileged `VITE_` variables, and Postgres DSNs with
a password. Files under `tools/`, `docs/`, `.github/` and `test_*` were
excluded as known false positives.

Findings: **0**.

## Rotate on this schedule

Anything below that has ever been set in a real environment should be
rotated, in this order. Highest blast radius first.

| Priority | Secret | Why it is at risk | How to rotate |
|---|---|---|---|
| 1 | `JWT_SECRET_KEY` | A leaked value lets an attacker mint a valid session for any user, including admin. Full takeover with no login. | Generate a new value, deploy it, then accept that existing tokens are invalid and force re-login. |
| 2 | `SECRET_KEY` (signing) | Any signature built on it is forgeable. | New value, redeploy, invalidate. |
| 3 | Supabase `service_role` key | Bypasses row-level security. Someone holding it reads every tenant. | Supabase dashboard: rotate the service key. Never place it in a `VITE_` variable. |
| 4 | Supabase anon key | Lower impact, but must match the new service key's project settings. | Same dashboard action. |
| 5 | `REDIS_PASSWORD` | Cache poisoning and session theft. | New value in `.env`, and in `REDIS_URL` on every service that connects. |
| 6 | `STRIPE_SECRET_KEY` | Direct financial manipulation. | Stripe dashboard: roll the secret key. |
| 7 | `STRIPE_WEBHOOK_SECRET` | Forged webhook; combined with the old missing mapping check, an account upgrade. | Stripe dashboard: roll the signing secret. |
| 8 | AI provider keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, others) | Direct monetary loss and prompt exfiltration. | Provider dashboard: revoke and reissue. |
| 9 | `GRAFANA_PASSWORD` / `GF_SECURITY_ADMIN_PASSWORD` | The default was the literal `admin`; a defaulted credential is an open monitoring console. | Set explicitly, then change from the default in the Grafana UI. |
| 10 | Database DSN password | Full data access. | Change the DB password, update every service's DSN. |

## How to rotate without downtime

1. Add the new secret alongside the old one. Most verifiers (`kms`,
   provider SDKs) accept a keylist.
2. Deploy the new value everywhere it is read.
3. Confirm health: `/health/components` and the Metrics dashboard.
4. Remove the old secret.
5. Invalidate sessions if the rotation was for `JWT_SECRET_KEY` or
   `SECRET_KEY`.

## The `.env` that was tracked

The junk `.env` was removed from the git index. It held placeholder
strings, not live credentials. It is now untracked and covered by
`.gitignore`. A new `.env.example` documents every required key so
nobody has to reconstruct the file from a broken one.

Because the file is absent from the working tree after the untrack, copy
`.env.example` to `.env` and fill in real values.

## Confirm each rotation

- `git log --all -- .env` returns nothing.
- `python tools/secret_scan.py` returns 0 findings.
- `gitleaks detect --source=. --redact` (CI already runs this) is clean.
- The `frontend-secret-audit` CI job passes, so no privileged key reached
  `src/`.
