#!/bin/bash
echo "Starting AstrovoxAI locally..."
echo ""
echo "Starting Backend (FastAPI)..."
cd 02-Backend || exit 1
python -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"
sleep 3
echo ""
echo "Starting Frontend (Next.js)..."
cd ../apps/web || exit 1
npm run dev &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"
echo ""
echo "========================================"
echo "  AstrovoxAI is starting..."
echo "  Backend: http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop both services"
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
