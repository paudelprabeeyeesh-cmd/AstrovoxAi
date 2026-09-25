# Coding Standards

## Python
- Format with `black` (line-length 100)
- Lint with `ruff`
- Type hints required for all public functions
- Docstrings for all public classes/functions
- Maximum complexity: 10
- Maximum function length: 50 lines

## TypeScript/React
- Format with `prettier`
- Lint with `eslint`
- TypeScript strict mode enabled
- Functional components with hooks
- No `any` types

## Git
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Branch naming: `feature/`, `fix/`, `release/`
- PR size: max 400 lines changed

## Testing
- Unit tests for all business logic
- Integration tests for API endpoints
- E2E tests for critical user flows
- Minimum 80% coverage for new code

## Security
- No secrets in code
- All user input validated
- SQL queries parameterized
- Dependencies audited weekly
