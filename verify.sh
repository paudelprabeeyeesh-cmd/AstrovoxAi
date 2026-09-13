#!/bin/bash
echo "=== AstrovoxAI Final Verification ==="
echo ""

# Check git status
echo "1. Git status:"
git status
echo ""

# Check recent commits
echo "2. Recent commits:"
git log --oneline -10
echo ""

# Run tests
echo "3. Running tests..."
cd 02-Backend
python -m pytest tests/ -q
echo ""

# Verify app loads
echo "4. Verifying app loads..."
python -c "from app.main import app; print('App loads OK')"
echo ""

# Check file counts
echo "5. File counts:"
echo "   Python modules: $(find 02-Backend/app -name '*.py' | wc -l)"
echo "   Test files: $(find 02-Backend/tests -name '*.py' | wc -l)"
echo "   Docs: $(find . -maxdepth 1 -name '*.md' | wc -l)"
echo ""

echo "=== Verification Complete ==="
