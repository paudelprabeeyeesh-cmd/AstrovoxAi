#!/bin/bash
set -euo pipefail

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 2.1.0"
    exit 1
fi

echo "=== AstrovoxAI Release v$VERSION ==="

if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Uncommitted changes detected"
    git status --porcelain
    exit 1
fi

if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "Error: Tag v$VERSION already exists"
    exit 1
fi

echo "Running tests..."
cd 02-Backend
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing
cd ..

echo "Building Docker images..."
docker build -f Dockerfile.backend -t astrovoxai/backend:v$VERSION .
docker build -f Dockerfile.frontend -t astrovoxai/frontend:v$VERSION .

echo "Pushing images..."
docker push astrovoxai/backend:v$VERSION
docker push astrovoxai/frontend:v$VERSION

echo "Creating git tag..."
git tag -a "v$VERSION" -m "Release v$VERSION"
git push origin "v$VERSION"

echo "Release v$VERSION completed successfully!"
