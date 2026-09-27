# Contributing to AstrovoxAI

Thank you for your interest in contributing! This document explains how to set up the project, submit changes, and work with the maintainers.

## Code of Conduct

By participating, you agree to uphold our [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+
- Go 1.21+
- JDK 17+
- Rust 1.70+
- Git
- Docker and Docker Compose
- PostgreSQL 14+
- Redis 7+

### Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/AstrovoxAi
   cd AstrovoxAi
   ```
3. Create a branch:
   ```bash
   git checkout -b feature/my-feature
   ```
4. Set up the development environment:
   ```bash
   cp .env.example .env
   # Fill in required environment variables
   docker-compose up -d postgres redis
   ```

## Development

### Backend (Python)

```bash
cd 02-Backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

### SDKs

```bash
cd sdk/python
pip install -e .

cd sdk/typescript
npm install
npm run build

cd sdk/go
go mod tidy

cd sdk/java
mvn install

cd sdk/rust
cargo build
```

## Submitting Changes

1. Keep changes focused and minimal.
2. Update docs/tests when behavior changes.
3. Ensure linting passes:
   ```bash
   ruff check .
   npm run lint
   ```
4. Write tests for new functionality.
5. Open a Pull Request with a clear description.

## Pull Request Checklist

- [ ] Tests added or updated
- [ ] Documentation updated
- [ ] Lint passes
- [ ] Type checking passes
- [ ] CHANGELOG.md updated (if applicable)

## Reporting Bugs

Open an issue with:
1. Steps to reproduce
2. Expected behavior
3. Actual behavior
4. Environment details (OS, version, etc.)

## Feature Requests

Open an issue first to discuss proposed changes.

## Questions

Join our [Discord](https://discord.gg/astrovox) or open a [GitHub Discussion](https://github.com/YOUR_USERNAME/AstrovoxAi/discussions).
