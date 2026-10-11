# ADR-0006: Quarantine experimental modules out of the product path

- Status: accepted
- Date: 2026-10-10
- Task: D01-10, D01-11

## Context

A static import graph over `02-Backend/app/` (1,503 files) found 114 top-level
packages and modules, of which only **7** are imported by product code:
`app`, `routes`, `api_gateway`, `sandboxing`, `database`, `retrieval`,
`memory_persistence`. The remaining 107 include many NumPy simulations for
research topics that nothing in the product calls.

Carrying them inside the product path has three costs: dead code that still has
to compile, an implied capability the product does not have, and a wide blast
radius for any refactor.

## Decision

Treat "imported by `app/`" as the definition of live. Everything else is lab
code. Enforcement is mechanical rather than convention: `tools/check_live_imports.py`
walks the live modules and exits non-zero if any of them imports an experimental
module. It runs in pre-commit and CI, so the boundary cannot drift silently.

The modules themselves are not deleted — they may still be useful — but they are
labelled in `docs/MODULE_INVENTORY.md` and excluded from the product test suite.

## Consequences

- Product code cannot gain a dependency on experimental code without a failing
  check, so the live surface can only shrink or stay the same by choice.
- Public claims must not reference capabilities that only exist behind the
  quarantine (see `docs/POSITIONING.md`).
- Reviving a quarantined module is a two-step process: move it back, then fix
  the import surface the check will flag.

## Alternatives considered

- Delete the modules outright. Too aggressive; the learning value is real and
  the repo is the only copy.
- Move them to `experiments/` in one commit. Higher risk (renames across the
  whole tree) for no additional safety, because the import check already
  provides the guarantee.