<<<<<<< HEAD
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

=======
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

>>>>>>> 10617909505295e4a37b817bb54db2364934b978
### Backend

```bash
cd 02-Backend
<<<<<<< HEAD
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

### Model Development

```bash
# Install ML dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Verify installation
pytest tests/ -v

# Train a tiny model (CPU-friendly)
python examples/train_tiny.py --config models/llm/configs/config_100m.yaml

# Run inference
python examples/generate.py --prompt "Hello world" --checkpoint model.pt
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
├── models/                     # LLM model code
│   └── llm/
│       ├── model/              # Transformer architecture
│       ├── trainer/            # Pre-training and fine-tuning
│       ├── tokenizer/          # Tokenizer training
│       ├── inference/          # Generation engine + FastAPI server
│       ├── evaluation/         # Benchmark harness
│       ├── quantization.py     # INT8/FP16/BF16 quantization
│       ├── export.py           # Multi-format model export
│       └── configs/            # Model size configs
├── examples/                   # Developer examples
├── tests/                      # Test suites
├── docs/                       # Documentation
├── sdk/                        # Generated SDKs
├── charts/                     # Helm charts
├── k8s/                        # Kubernetes manifests
├── monitoring/                 # Prometheus/Grafana configs
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

### Python (Model)

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Write docstrings for public functions and classes
- Use `torch.compile` when available for performance
- Keep model classes pure (no side effects in forward)
- Use `torch.no_grad()` for inference
- Prefer `torch.compile` over manual optimization

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
    pytest tests/ -v
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

### Model Tests

```bash
# Run all model tests
pytest tests/ -v

# Run specific test file
pytest tests/test_model.py -v

# Run with coverage
pytest tests/ --cov=models --cov-report=term-missing
```

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
=======
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
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
