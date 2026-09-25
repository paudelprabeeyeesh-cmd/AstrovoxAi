# API Versioning Policy

## Current Version
- **v1**: Current production API under `/v1/` prefix
- **v0**: Legacy unversioned endpoints (`/solve`, `/memory`, etc.) - deprecated

## Versioning Strategy
- URL path versioning: `/v1/`, `/v2/`
- Deprecation period: 6 months
- Sunset period: 3 months after deprecation
- Breaking changes require new minor version

## Lifecycle
1. **Deprecated**: Header `Sunset: <date>` added
2. **Sunset**: Returns `410 Gone`
3. **Removed**: Code deleted after sunset date

## Headers
- `API-Version`: Current API version
- `Sunset`: Deprecation date
- `Deprecation`: `true` if deprecated

## Migration Guide
- See `/docs/versioning` for migration examples
