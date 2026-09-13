# Contributing to AstrovoxAI

Thank you for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/AstrovoxAi.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `pytest` and `npm run lint`
6. Commit and push
7. Open a Pull Request

## Development Setup

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

## Coding Standards

- Python: Follow PEP 8, use type hints
- JavaScript/React: Follow ESLint config
- Write tests for new features
- Document public APIs

## Testing

```bash
# Backend tests
cd 02-Backend
pytest

# Frontend lint
npm run lint

# Frontend typecheck
npm run typecheck
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Fill out the PR template
5. Request review

## Code of Conduct

Be respectful and constructive. We welcome all contributors.
