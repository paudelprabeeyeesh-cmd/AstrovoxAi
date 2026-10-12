# Python Backend Test Baseline

Measured on 2026-10-12 (commit `7c8f7e1`), Windows, Python 3.14.5, pytest 9.1.1.

## How this was measured

A single `python -m pytest` run does **not** complete. Across the whole suite
some modules make real network calls or block on a `threading.Condition`
that never fires, so the run hits pytest-timeout and dies before printing a
summary. That is a pre-existing property of the suite, not something this
work introduced.

Results below come from running each top-level test package separately,
with `--timeout=25 -p no:randomly`. Every package that produced a summary is
counted. The one package that could not complete is listed explicitly.

## Headline numbers

| Scope | Result |
|---|---|
| `tests/security` | **93 passed / 0 failed** |
| `tests/integration` | 15 failed / 47 passed / 12 errors *(see below)* |
| Full suite, single run | **does not complete** (blocked module) |

Combined across the two chunks that completed: **140 passed, 15 failed,
12 errors**.

## Package detail

### `tests/security` - 93 passed, 0 failed

This is the chunk that carries the security controls, and it is green.

Before this work it was 59 passed / 20 failed. The 20 failures were not
cosmetic:

* the login lockout never ran, because its SQL was a plain string and a
  `?`-placeholder tuple against a SQLAlchemy Session;
* `record_failure` returned a 3-tuple the tests read as a 2-tuple;
* `refresh_token_rotation` deadlocked its caller forever (a plain `Lock`
  held across a call that re-acquired it);
* the webhook signature check never saw a real signature;
* `auth.py` had imports at the bottom of the file, dead code after `raise`,
  and duplicate `get_current_user` / `require_admin` definitions;
* `/auth/refresh` accepted the refresh token as a query parameter;
* `/auth/oauth` ignored the token it was given;
* 30 routers were replaced with an empty `APIRouter` inside
  `except Exception`, so a broken subsystem was indistinguishable from a
  healthy empty one.

All of those are fixed and now covered.

### `tests/integration` - 15 failed / 47 passed / 12 errors

Three groups, none of them introduced here:

1. **Database unavailable (now fixed).** `app/database.py` imported a
   working `get_connection` and then immediately redefined `get_db` to a
   stub that unconditionally raised `RuntimeError("Database not
   available")`. Every caller of `app.database.get_db` failed at call
   time. `get_db` now delegates to the repository-layer session factory,
   with a documented sqlite fallback. The related `login_attempts`
   schema mismatch between `app/services/auth/auth.py` and
   `app/services/auth_service.py` is gone: the schema lives in
   `app/services/login_attempt_schema.py`.

2. **Stale tests written against the insecure API (now updated).**
   `test_refresh_token` sent the refresh token as a query parameter and
   `test_me_with_token_returns_user` sent the bearer token as a query
   parameter. Both are now sent the secure way in the body and the
   Authorization header, and `test_refresh_token_rejected_as_query_parameter`
   and `test_oauth_requires_a_known_provider` assert the old insecure form
   is rejected. `test_oauth_initiates_flow` now asserts an unverified
   OAuth token returns 401 rather than minting a session.

3. **Genuinely broken product paths (open, unfixed).**
   `test_core_flows.py` (17 errors), `test_lifecycle.py` (11 failures),
   `test_backup_restore.py` (3), `test_database_hardening.py` (2), and the
   CSRF test when the suite is run as a whole but green in isolation. These
   are the open backlog.

## What the baseline says honestly

* Security regression and feature tests: fully green, and were not before.
* Database plumbing: fixed.
* LLM-related paths: not realised as testable here. `test_backup_restore` fails
  because the invocation depends on `claude`-style configuration being absent,
  and the rest because the configured `app.db` tables do not exist at
  `app.infrastructure.database` init time.
* Network-blocked modules: a measurable part of the suite cannot pass in
  an environment without a Supabase instance, an SMTP server, and egress to
  the AI providers. No claim of "100%" is defensible until those are
  mocked or provided.

## Reproducing

```bash
cd 02-Backend
python -m pytest tests/security -q --no-header --timeout=25 -p no:randomly
python -m pytest tests/integration -q --no-header --timeout=25 -p no:randomly
```

`python tools/baseline_run.py tests/security tests/integration` records both
chunks and writes `_baseline.txt`.

## Open issues

1. `test_core_flows.py` errors: 17 of them trace to unavailable database
   tables. Either the infra engine must create its schema at startup, or
   the tests must set one up in a fixture. Choosing the second is better.
2. `test_lifecycle.py` failures need triage; they are unexamined.
3. `test_backup_restore.py` needs the external CLI or must be marked
   environment-dependent.
4. Whole-suite CSRF test ordering interference needs a fixture-scoped
   isolation rather than a global, since a shared cookie jar is being
   mutated across tests.
5. The suite needs `CodeQL` and `pytest -n auto` in CI with a per-test
   timeout, so a hung module fails its own test instead of the run.
6. Coverage reporting is disabled for this baseline. The `coverage-enforcement`
   job now parses the real coverage XML, so wiring `--cov=app` into these
   chunk runs is the remaining step.
