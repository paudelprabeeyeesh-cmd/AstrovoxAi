# Contributing to AstrovoxAi

Thank you for your interest in contributing. This document explains how to set up the project, submit changes, and work with the maintainers.

## Code of Conduct

Be respectful. Constructive feedback only. No harassment or discrimination.

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.9+
- Git
- Docker (optional but recommended)

### Setup

1. Fork the repository and clone your fork:
   ```bash
   git clone https://github.com/<your-username>/AstrovoxAi.git
   cd AstrovoxAi
   ```

2. Install backend dependencies:
   ```bash
   cd 02-Backend
   pip install -r requirements.txt
   ```

3. Install frontend dependencies:
   ```bash
   npm install
   ```

4. Copy `.env.example` to `.env` and fill in your local values.

5. Run the backend:
   ```bash
   cd 02-Backend
   python -m uvicorn app.main:app --reload
   ```

6. Run the frontend:
   ```bash
   npm run dev
   ```

## Project Structure

- `02-Backend/app/` — FastAPI backend
  - `kernel/` — Core runtime, scheduler, event bus
  - `executor/` — DSL parser, compiler, runtime
  - `enterprise/` — Organization and RBAC logic
  - `providers/` — AI provider integrations
- `02-Backend/tests/` — Backend test suite
- `src/` — React frontend
- `database/` — SQL schemas and migrations

## How to Contribute

1. Create a branch from `main`:
   ```bash
   git checkout -b feature/my-change
   ```

2. Make your change. Follow the existing code style.

3. Run the relevant tests:
   ```bash
   cd 02-Backend
   pytest
   ```

4. Run linting if available:
   ```bash
   npm run lint
   ```

5. Commit with a clear message:
   ```bash
   git commit -m "feat: add summary"
   ```

6. Push and open a pull request.

## Pull Request Guidelines

- Keep changes focused. One feature or fix per PR.
- Update documentation if you change behavior.
- Ensure tests pass before requesting review.
- Link to any related issues.

## Reporting Bugs

Open an issue with:

- A clear title
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, browser)

## Feature Requests

Open an issue with:

- A clear description of the feature
- Why it is useful
- Possible implementation approach

## Questions

Open an issue with the `question` label.
