# Contributing to AstrovoxAI

Thank you for your interest in contributing to AstrovoxAI. This document explains how to set up the project, submit changes, and work with the maintainers.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Standards](#code-standards)
- [Submitting Changes](#submitting-changes)
- [Testing](#testing)
- [Documentation](#documentation)
- [Security Policy](#security-policy)
- [Release Process](#release-process)
- [Community](#community)

## Code of Conduct

Be respectful. Constructive feedback only. No harassment or discrimination. By participating, you agree to uphold this standard.

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.9+
- Git
- Docker & Docker Compose (recommended)
- Supabase account (for database)

### Setup

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/AstrovoxAi.git
   cd AstrovoxAi
   ```
3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/astrovox/AstrovoxAi.git
   ```
4. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

## Development Setup

### Backend

```bash
cd 02-Backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
npm install
npm run dev
```

### Environment

```bash
cp .env.example .env
# Edit .env with your Supabase and AI provider keys
```

## Project Structure

```
AstrovoxAi/
├── src/                        # React frontend (Vite + TypeScript)
├── 02-Backend/                 # FastAPI backend
│   └── app/
│       ├── main.py             # FastAPI app entry point
│       ├── api/                # API routers
│       ├── providers/          # AI provider implementations
│       ├── middleware/         # Security & request middleware
│       └── services/           # Business logic services
├── database/                   # Database schemas and migrations
├── docs/                       # Documentation
├── sdk/                        # Generated SDKs
├── charts/                     # Helm charts
├── k8s/                        # Kubernetes manifests
├── monitoring/                 # Prometheus/Grafana configs
├── tests/                      # Test suites
└── tools/                      # Development tools
```

## Code Standards

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Use async/await for all I/O operations
- Maximum line length: 100 characters
- Use `ruff` for linting and formatting

### TypeScript (Frontend)

- Use strict TypeScript mode
- Follow React best practices (functional components, hooks)
- Use Tailwind CSS for styling
- Write unit tests with Vitest
- Use ESLint with the project's configuration

### Git Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only changes
- `style:` — Formatting, missing semicolons, etc.
- `refactor:` — Code change that neither fixes a bug nor adds a feature
- `perf:` — Performance improvement
- `test:` — Adding or updating tests
- `chore:` — Maintenance tasks

## Submitting Changes

### Pull Request Process

1. Ensure all tests pass:
   ```bash
   cd 02-Backend && pytest
   npm run test:all
   ```
2. Update documentation if behavior changes
3. Keep changes focused and minimal
4. Open a Pull Request against the `main` branch
5. Fill in the PR template completely
6. Request review from maintainers

### PR Requirements

- All CI checks must pass
- Code coverage must not decrease
- Documentation updated for public API changes
- CHANGELOG.md updated for user-facing changes
- No secrets or credentials in code

## Testing

### Backend Tests

```bash
cd 02-Backend
pytest                    # Run all tests
pytest -x                 # Stop on first failure
pytest --cov              # With coverage report
pytest tests/unit/        # Unit tests only
pytest tests/integration/ # Integration tests
```

### Frontend Tests

```bash
npm run test:unit          # Unit tests
npm run test:integration   # Integration tests
npm run test:e2e           # End-to-end tests
npm run test:security      # Security tests
npm run test:all           # Full test suite
```

### Code Quality

```bash
npm run quality:dashboard      # Quality dashboard
npm run quality:dead-code      # Dead code detection
npm run quality:security       # Security linting
```

## Documentation

- Update docs when behavior changes
- Add examples for new API endpoints
- Update README.md for new features
- Keep API.md in sync with code changes

## Security Policy

Please report security vulnerabilities privately via [SECURITY.md](SECURITY.md). Do not open public issues for security bugs.

## Release Process

1. Update version in `package.json` and `pyproject.toml`
2. Update CHANGELOG.md
3. Create a release branch
4. Run full test suite
5. Tag release and push
6. GitHub Actions handles deployment

## Community

- Join our [Discord](https://discord.gg/astrovox)
- Open a [GitHub Discussion](https://github.com/astrovox/AstrovoxAi/discussions)
- Follow us on [Twitter](https://twitter.com/astrovoxai)

Thank you for contributing to AstrovoxAI!
