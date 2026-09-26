# Contributing to AstrovoxAI

Thank you for your interest in contributing! This guide covers the development workflow, code standards, and review process.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Branch Naming](#branch-naming)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Review Process](#review-process)
- [Release Process](#release-process)
- [Roadmap](#roadmap)
- [Community](#community)

---

## Code of Conduct

By participating, you agree to uphold our [Code of Conduct](CODE_OF_CONDUCT.md).

Be respectful, constructive, and collaborative. We are here to build great software together.

---

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/astrovox.git
   cd astrovox
   ```
3. Create a branch:
   ```bash
   git checkout -b feature/your-feature
   ```
4. Make your changes
5. Run tests:
   ```bash
   npm run test:all
   npm run lint
   ```
6. Commit and push:
   ```bash
   git push origin feature/your-feature
   ```
7. Open a Pull Request

---

## Development Setup

### Prerequisites

- Node.js 18+ and npm 9+
- Python 3.9+ and pip
- Git
- Docker & Docker Compose (optional)
- Supabase account (for local development)

### Frontend Setup

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Run lint
npm run lint

# Type check
npm run typecheck

# Run tests
npm run test
```

### Backend Setup

```bash
cd 02-Backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your Supabase and AI provider keys

# Run database migrations
# Execute database/schemas/supabase_setup.sql in Supabase SQL Editor

# Start backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest
```

### Docker Setup

```bash
# Copy environment
cp .env.example .env
nano .env

# Start all services
docker-compose up --build
```

### SDK Development

```bash
# Python SDK
cd sdk/python
pip install -e .
pytest

# TypeScript SDK
cd sdk/typescript
npm install
npm run build
npm test
```

---

## Branch Naming

Follow these conventions:

| Type | Example |
|------|---------|
| Feature | `feature/add-voice-input` |
| Bug fix | `fix/streaming-timeout` |
| Documentation | `docs/update-api-reference` |
| Refactoring | `refactor/simplify-provider-factory` |
| Test | `test/add-chat-streaming-tests` |
| Chore | `chore/update-dependencies` |
| Hotfix | `hotfix/security-patch-cors` |

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

### Types

- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation changes
- `style` — Code style changes (formatting, missing semicolons)
- `refactor` — Code refactoring
- `test` — Test additions/fixes
- `chore` — Maintenance tasks
- `perf` — Performance improvements

### Examples

```
feat(chat): add streaming support for Claude 3.5 Sonnet

Implements SSE streaming for Anthropic provider.
Adds retry logic with exponential backoff.
Updates provider factory to route streaming requests.

Closes #123
```

```
fix(memory): handle empty memory extraction gracefully

Previously, empty conversations caused a 500 error.
Now returns empty list with 200 status.

Fixes #456
```

```
docs(api): add embeddings endpoint documentation

Documents request/response schemas and error codes.
```

---

## Pull Request Process

1. **Create a draft PR early** for feedback on approach
2. **Keep PRs focused** — one feature or fix per PR
3. **Update documentation** for any changed functionality
4. **Add tests** for any new functionality
5. **Ensure all checks pass**:
   ```bash
   npm run lint
   npm run typecheck
   npm run test:all
   ```
6. **Request review** from maintainers
7. **Address review feedback** promptly
8. **Squash commits** if requested before merge

### PR Title Format

Same as commit messages:
```
feat(chat): add voice input support
```

---

## Code Standards

### Python (Backend)

- Follow [PEP 8](https://pep8.org/)
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use `ruff` for linting and formatting
- Docstrings for all public functions/classes (Google style)
- Async/await for all I/O operations
- Use Pydantic models for request/response validation

**Example:**
```python
from pydantic import BaseModel, Field
from typing import Optional

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    model: str = Field(default="gpt-4", min_length=1, max_length=64)


async def create_conversation(
    user_id: str,
    request: CreateConversationRequest,
) -> dict:
    """Create a new conversation for the user.

    Args:
        user_id: The authenticated user's UUID.
        request: Conversation creation request.

    Returns:
        Created conversation object.
    """
    ...
```

### TypeScript / React (Frontend)

- TypeScript strict mode (`"strict": true`)
- Functional components with hooks
- Tailwind CSS for styling
- Accessible components (WCAG 2.2 AA)
- Maximum line length: 100 characters
- Meaningful component and variable names

**Example:**
```tsx
interface MessageProps {
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: Date;
}

export function Message({ content, role, timestamp }: MessageProps) {
  return (
    <div className={`message ${role}`}>
      <p>{content}</p>
      <time>{formatTime(timestamp)}</time>
    </div>
  );
}
```

### Testing Standards

- Unit tests for all new functions/classes
- Integration tests for API endpoints
- E2E tests for critical user flows
- All tests must pass before merge
- Aim for 80%+ code coverage

---

## Testing Requirements

### Backend Tests

```bash
cd 02-Backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_chat.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run integration tests
pytest tests/test_integration.py
```

### Frontend Tests

```bash
# Unit tests
npm run test:unit

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e

# All tests
npm run test:all
```

### Required Test Coverage

| Component | Minimum Coverage |
|-----------|------------------|
| Backend core modules | 80% |
| API endpoints | 90% |
| Frontend components | 70% |
| Critical paths (auth, chat) | 95% |

---

## Review Process

- At least one approval required from maintainers
- Address all review comments before merge
- Keep PRs focused and reasonably sized (< 400 lines)
- Break large changes into sequential PRs
- CI must pass (lint, typecheck, tests)

### Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No secrets or credentials committed
- [ ] Error handling is comprehensive
- [ ] Performance considerations addressed
- [ ] Backward compatibility maintained

---

## Release Process

1. Maintainers create release branch from `main`
2. Version bump in `package.json` and `pyproject.toml`
3. Update `CHANGELOG.md`
4. Create GitHub release with notes
5. Merge to `main` and tag release
6. Publish packages if applicable
7. Deploy to production via CI/CD

---

## Roadmap

### Current Release: v2.0.0

**Status**: Production-ready

#### Delivered
- [x] Multi-provider AI support (OpenAI, Anthropic, Gemini, Ollama, Groq)
- [x] Streaming responses via SSE
- [x] Persistent conversation memory
- [x] RAG (Retrieval-Augmented Generation)
- [x] Agent system with tool use
- [x] React SDK and web components
- [x] Python and TypeScript SDKs
- [x] Docker deployment
- [x] CI/CD pipeline with GitHub Actions
- [x] Monitoring with Prometheus + Grafana
- [x] Security hardening and audit logging
- [x] Team workspaces
- [x] Plugin marketplace foundation
- [x] Webhook integrations

### In Progress

- [ ] Multi-modal support (images, audio, video)
- [ ] Voice conversations with real-time transcription
- [ ] Plugin marketplace for third-party extensions
- [ ] Advanced analytics dashboard
- [ ] Mobile apps (iOS, Android)
- [ ] Desktop app (Tauri)

### Planned (Q1-Q2 2025)

- [ ] Custom model fine-tuning API
- [ ] Workflow automation engine
- [ ] Code interpreter with sandboxed execution
- [ ] Multi-language support (i18n)
- [ ] Enterprise SSO (SAML, OIDC)
- [ ] HIPAA-compliant deployment option

### Backend Hardening

#### Phase 1: Stabilize
- [x] Centralize shared utilities
- [ ] Instrument exception subclasses with structured context
- [ ] Configure pytest with strict markers and coverage thresholds
- [ ] Run `ruff check .` and `mypy app/` in CI
- [ ] Add unhandled exception handler in ASGI middleware

#### Phase 2: Simplify
- [ ] Audit file count and module responsibilities
- [ ] Consolidate single-class subpackages
- [ ] Eliminate enum duplication
- [ ] Remove dead imports and unused dependencies

#### Phase 3: Optimize
- [ ] Baseline profiling with cProfile
- [ ] Startup time reduction via lazy-loading
- [ ] Memory footprint optimization with bounded LRU caches
- [ ] Async I/O audit

#### Phase 4: Harden
- [ ] Security audit with bandit and pip-audit
- [ ] Wrap external HTTP calls with retry policies
- [ ] Crash recovery and checkpoint testing

---

## Community

- **Issues**: [GitHub Issues](https://github.com/astrovox/astrovox/issues)
- **Discussions**: [GitHub Discussions](https://github.com/astrovox/astrovox/discussions)
- **Security**: See [SECURITY.md](SECURITY.md)

## License

MIT License — see [LICENSE](LICENSE) for details.
