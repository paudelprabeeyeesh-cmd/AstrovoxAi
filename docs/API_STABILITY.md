# API Stability & Versioning Policy

## Versioning

Astrovox follows Semantic Versioning 2.0.0 (`MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`).

- `MAJOR` increments for breaking API changes.
- `MINOR` increments for backward-compatible functionality.
- `PATCH` increments for backward-compatible bug fixes.
- `PRERELEASE` labels such as `rc1`, `beta`, `alpha` indicate non-stable builds.
- `BUILD` metadata may encode commit hashes or build numbers.

Current stable series: `1.0.x`.
Current pre-release series: `1.0.0-rc1`.

## Stability Guarantees

- Public APIs in `astrovox.*` are considered stable once a major version is released.
- Experimental modules are namespaced under `astrovox.experimental.*`.
- Internal modules under `astrovox._internal.*` may change without notice.
- CLI flags, environment variables, and config formats in stable releases are backward compatible within the same major version.

## Deprecation Policy

- Deprecated APIs remain functional for at least two minor releases.
- Deprecation warnings must be emitted via `warnings.warn(..., DeprecationWarning, stacklevel=2)`.
- Migration guidance must be included in release notes and documentation.

## Breaking Change Process

1. Propose breaking changes via an Architecture Decision Record (ADR).
2. Provide a migration guide and codemod when feasible.
3. Announce deprecation in the current minor release.
4. Remove or change behavior in the next major release.

## Compatibility

- Supported Python versions are declared in `pyproject.toml` and CI matrices.
- Supported OS targets: Linux, macOS, Windows.
- Third-party dependency compatibility is verified via `pip-audit` and dependency-update CI.
