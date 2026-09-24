# Contributing

Thank you for your interest in contributing to AstrovoxAI!

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Accept responsibility and apologize for mistakes

## How to Contribute

### Reporting Bugs

1. Search existing issues to avoid duplicates
2. Use the bug report template
3. Include:
   - Python/Node version
   - OS
   - Steps to reproduce
   - Expected vs actual behavior
   - Logs or error messages

### Suggesting Features

1. Open a GitHub Discussion first
2. Explain the use case and expected behavior
3. Wait for maintainer feedback before coding

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Add tests for new functionality
5. Ensure CI passes (lint, typecheck, tests)
6. Submit a PR with a clear description

## Development Setup

```bash
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi
cp .env.example .env
docker compose up -d postgres redis
cd 02-Backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd frontend/apps/web && npm install
```

## Code Standards

### Python

- Format with `black`
- Lint with `ruff`
- Type hints required for public functions
- Docstrings for all public methods

```python
async def get_user(user_id: str) -> User | None:
    """Fetch a user by ID.
    
    Args:
        user_id: UUID of the user.
    
    Returns:
        User object or None if not found.
    """
    ...
```

### TypeScript/React

- Use functional components with hooks
- Prefer `const` over `let`
- Use explicit return types
- Follow ESLint rules

### Commits

Follow Conventional Commits:
- `feat: add user profile endpoint`
- `fix: resolve memory leak in chat service`
- `docs: update deployment guide`
- `test: add pagination tests`
- `chore: update dependencies`

## Testing

### Backend

```bash
cd 02-Backend
pytest tests/ -v --cov=app
```

Requirements:
- All new features must have tests
- Existing tests must pass
- Aim for 80%+ coverage

### Frontend

```bash
cd frontend/apps/web
npm run test
npm run lint
npm run typecheck
```

## Review Process

1. Maintainer reviews within 48 hours
2. Address feedback promptly
3. Squash commits before merge
4. Delete branch after merge

## Community

- Join our Discord
- Attend weekly dev calls (Fridays 2pm UTC)
- Follow the project on Twitter/X

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
