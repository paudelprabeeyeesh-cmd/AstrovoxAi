# Contributing to AstrovoxAI

Thank you for your interest in contributing! This document explains how to set up the project, submit changes, and work with the maintainers.

## Code of Conduct

Be respectful. Constructive feedback only. No harassment or discrimination.

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.9+
- Git
- Docker (optional but recommended)

### Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/AstrovoxAi`
3. Create a branch: `git checkout -b feature/my-feature`
4. Make changes and commit: `git commit -am 'feat: add feature'`
5. Push: `git push origin feature/my-feature`
6. Open a Pull Request

## Development

### Backend

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

## Submitting Changes

- Keep changes focused and minimal.
- Update docs/tests when behavior changes.
- Open an issue first to discuss proposed changes.

## Feature Requests

Open an issue first to discuss proposed changes.

## Questions

Join our Discord or open a GitHub Discussion.
