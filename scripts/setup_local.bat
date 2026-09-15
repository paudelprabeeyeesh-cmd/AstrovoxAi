@echo off
echo ========================================
echo   AstrovoxAI - Local Development Setup
echo ========================================
echo.
echo [1/4] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.12+
    pause
    exit /b 1
)
echo.
echo [2/4] Checking Node.js...
node --version
if errorlevel 1 (
    echo ERROR: Node.js not found. Install Node.js 18+
    pause
    exit /b 1
)
echo.
echo [3/4] Setting up Backend...
cd 02-Backend
echo Installing Python dependencies...
pip install -r requirements.txt
echo.
echo [4/4] Setting up Frontend...
cd ../apps/web
echo Installing Node dependencies...
npm install
echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo To run locally:
echo   1. Start PostgreSQL and Redis
echo   2. Set DATABASE_URL and REDIS_URL in .env
echo   3. Backend: cd 02-Backend ^& python -m uvicorn app.main:app --reload
echo   4. Frontend: cd apps/web ^& npm run dev
echo.
pause