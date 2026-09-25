# Contributing to Astrovox AI

Thank you for your interest in contributing! This guide covers the development workflow, code standards, and review process.

## Code of Conduct

By participating, you agree to uphold our [Code of Conduct](./CODE_OF_CONDUCT.md).

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/astrovox/astrovox.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `npm run test:all` and `npm run lint`
6. Commit and push
7. Open a Pull Request

## Development Setup

### Prerequisites

- Node.js 18+
- Python 3.9+
- Git
- Docker & Docker Compose (optional)

### Backend

```bash
cd 02-Backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Frontend

```bash
npm install
npm run dev
```

### SDKs

```bash
# Python SDK
cd sdk/python
pip install -e .

# TypeScript SDK
cd sdk/typescript
npm install
npm run build
```

## Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Test additions/fixes
- `chore/description` - Maintenance tasks

## Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions/fixes
- `chore`: Maintenance tasks

Example:
```
feat(chat): add streaming support for Claude models

Implements SSE streaming for Anthropic provider.
Adds retry logic with exponential backoff.

Closes #123
```

## Pull Request Process

1. **Create a draft PR early** for feedback on approach
2. **Update documentation** for any changed functionality
3. **Add tests** for any new functionality
4. **Ensure all checks pass**:
   - `npm run lint`
   - `npm run typecheck`
   - `npm run test:all`
5. **Request review** from maintainers
6. **Address review feedback** promptly
7. **Squash commits** if requested before merge

## Code Standards

### Python

- Follow PEP 8
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use `ruff` for linting and formatting
- Docstrings for all public functions/classes

### TypeScript/React

- Use TypeScript strict mode
- Follow React best practices (hooks, functional components)
- Use Tailwind CSS for styling
- Accessible components (WCAG 2.2 AA)
- Maximum line length: 100 characters

## Testing Requirements

- Unit tests for new functions/classes
- Integration tests for API endpoints
- E2E tests for critical user flows
- All tests must pass before merge
- Aim for 80%+ code coverage

## Review Process

- At least one approval required from maintainers
- Address all review comments before merge
- Keep PRs focused and reasonably sized (< 400 lines)
- Break large changes into sequential PRs

## Release Process

1. Maintainers create release branch from `main`
2. Version bump in `package.json` and `pyproject.toml`
3. Update `CHANGELOG.md`
4. Create GitHub release with notes
5. Merge to `main` and tag release
6. Publish packages if applicable
