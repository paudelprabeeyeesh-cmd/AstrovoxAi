# ADR-0009: One auth module; module/package shadowing removed

- Status: accepted
- Date: 2026-10-10
- Tasks: D05-02, D06-02, D06-03

## Context

`app/auth.py` (module) and `app/auth/` (package) shared a name. The package wins
an import, so the route handlers that lived in the module were unreachable by
name. To keep them importable, `app/auth/__init__.py` loaded the file with
`importlib` under a private name and re-exported its symbols.

That made the failure mode subtle: a test patching `app.auth.supabase` patched the
*package* attribute, while the handler read its own *module* global. The patch
appeared to succeed and the handler still made a real network call. Two separate
router registrations of the same path also made it ambiguous which handler was
live.

## Decision

Merge the legacy module into `app/auth/__init__.py` so the handlers and their
module globals are the same object, then delete `app/auth.py`. One module, one
set of globals, one registration per route.

Also removed by consequence: an empty stub `refresh_token` handler that registered
a route before the real one and returned `None`, and a duplicated
`except Exception:` clause that swallowed exceptions into an empty response.

## Consequences

- `patch.object(app.auth, "supabase", ...)` now patches what the handler reads,
  which is the only reason those tests can run without a live Supabase.
- The `importlib` shim and the private-name indirection are gone.
- Route registrations are unique per method and path, so the live handler is not
  order-dependent.
- Remaining risk: the merged file is ~670 lines. Splitting it into
  `app/auth/{router,sessions,tokens}.py` is the natural next step, but any split
  must keep the module-level globals that tests patch in one place.

## Alternatives considered

- Rename the package and keep the module. Rejected: preserves two auth
  implementations and the same patching ambiguity.
- Move tests to patch the handler's module directly. Rejected: couples tests to
  an implementation artefact caused by the shadowing.