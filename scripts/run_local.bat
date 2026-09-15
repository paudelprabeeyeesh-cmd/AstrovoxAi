@echo off
echo Starting AstrovoxAI locally...
echo.
echo Starting Backend (FastAPI)...
start "AstrovoxAI Backend" cmd /k "cd 02-Backend && python -m uvicorn app.main:app --reload --port 8000"
timeout /t 3 /nobreak >nul
echo.
echo Starting Frontend (Next.js)...
start "AstrovoxAI Frontend" cmd /k "cd apps/web && npm run dev"
echo.
echo ========================================
echo   AstrovoxAI is starting...
echo ========================================
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8000/docs
echo ========================================
pause