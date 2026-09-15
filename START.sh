#!/bin/bash
echo "========================================"
echo "  AstrovoxAI - Starting Locally"
echo "========================================"
echo ""

if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and fill in your values."
    exit 1
fi

if [ ! -d venv ]; then
    echo "ERROR: Python virtual environment not found!"
    echo "Please run: python -m venv venv"
    exit 1
fi

echo "Starting Backend..."
cd 02-Backend || exit 1
source ../venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
