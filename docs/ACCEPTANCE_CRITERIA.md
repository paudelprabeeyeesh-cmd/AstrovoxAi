# Acceptance Criteria for Core Changes

Use this document when evaluating whether a proposed change belongs in the
Astrovox core library.

## Mandatory Requirements

1. **Tested**: the change includes automated tests that fail without it.
2. **Documented**: public API surface has docstrings and, where appropriate,
   examples in `docs/`.
3. **Performance-aware**: benchmarks exist for performance-sensitive paths,
   and the change does not regress latency or throughput by more than 10%
   without an explicit, accepted tradeoff.
4. **Security-reviewed**: the change has been checked against `bandit`,
   `pip-audit`, and this project's threat model.
5. **Backward compatible**: unless the change is part of an approved major
   version bump, existing public APIs and configs continue to work.

## Preferred Characteristics

- The change solves a demonstrated user or product need rather than adding
  optional complexity.
- The implementation is localized; broad rewrites are discouraged unless
  paired with a migration plan.
- Experimental behavior lives under `astrovox.experimental.*` and is
  gated behind an opt-in flag.

## Rejection Signals

- Adds a third-party dependency without a clear, recurring need.
- Requires users to change working code without migration tooling.
- Increases binary size or startup time meaningfully without measurement.
- Duplicates functionality already available in an existing module.
