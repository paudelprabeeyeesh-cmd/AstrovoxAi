#!/bin/bash
echo "========================================"
echo "  AstrovoxAI - Local Development Setup"
echo "========================================"
echo ""
echo "[1/4] Checking Python..."
python3 --version || python --version
if [ $? -ne 0 ]; then
    echo "ERROR: Python not found. Install Python 3.12+"
    exit 1
fi
echo ""
echo "[2/4] Checking Node.js..."
node --version
if [ $? -ne 0 ]; then
    echo "ERROR: Node.js not found. Install Node.js 18+"
    exit 1
fi
echo ""
echo "[3/4] Setting up Backend..."
cd 02-Backend || exit 1
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo ""
echo "[4/4] Setting up Frontend..."
cd ../apps/web || exit 1
echo "Installing Node dependencies..."
npm install
echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "To run locally:"
echo "  1. Start PostgreSQL and Redis"
echo "  2. Set DATABASE_URL and REDIS_URL in .env"
echo "  3. Backend: cd 02-Backend && python -m uvicorn app.main:app --reload"
echo "  4. Frontend: cd apps/web && npm run dev"
echo ""